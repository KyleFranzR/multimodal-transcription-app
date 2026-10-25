
import json
import os
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

RATE = 16000
TARGET_PEAK = 0.8 * 32767
MAX_GAIN = 30.0
SETTINGS = Path.home() / ".caecus_settings.json"
_HIDDEN = ("sound mapper", "primary sound", "stereo mix", "midi")

_PIPEWIRE_SOURCES = {}


def _get_pipewire_sources():
    """Return available PipeWire input sources as display-name to node-name mappings."""
    global _PIPEWIRE_SOURCES

    if not shutil.which("pw-dump"):
        _PIPEWIRE_SOURCES = {}
        return {}

    try:
        result = subprocess.run(
            ["pw-dump"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        objects = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        _PIPEWIRE_SOURCES = {}
        return {}

    sources = {}

    for item in objects:
        if item.get("type") != "PipeWire:Interface:Node":
            continue

        props = item.get("info", {}).get("props", {})
        if props.get("media.class") != "Audio/Source":
            continue

        node_name = props.get("node.name")
        if not node_name:
            continue

        display_name = (
            props.get("node.nick")
            or props.get("node.description")
            or node_name
        )

        display_name = display_name.strip()

        if not display_name:
            display_name = node_name

        if any(term in display_name.lower() for term in _HIDDEN):
            continue

        label = display_name
        suffix = 2

        while label in sources and sources[label] != node_name:
            label = f"{display_name} ({suffix})"
            suffix += 1

        sources[label] = node_name

    _PIPEWIRE_SOURCES = sources
    return sources


def input_devices():
    """Return unique microphone names for the input-device dropdown."""
    sources = _get_pipewire_sources()
    names = list(sources.keys())

    try:
        host = sd.default.hostapi
        devices = [
            device
            for device in sd.query_devices()
            if device["max_input_channels"] > 0
        ]
        devices.sort(key=lambda device: device["hostapi"] != host)

        for device in devices:
            name = device["name"].strip()

            if not name or name.lower() in ("default", "pipewire"):
                continue

            if any(term in name.lower() for term in _HIDDEN):
                continue

            if name not in names:
                names.append(name)

    except Exception:
        pass

    return names


def load_choice():
    """Return the environment-selected or previously saved microphone name."""
    want = os.environ.get("CAECUS_MIC", "").strip()

    if want:
        return want

    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return settings.get("mic", "")
    except (OSError, ValueError, TypeError):
        return ""


def save_choice(name):
    """Save the selected microphone name."""
    try:
        SETTINGS.write_text(
            json.dumps({"mic": name}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _pick_sounddevice():
    """Resolve a legacy PortAudio device selection."""
    want = load_choice()

    if not want or want.lower() in ("default", "pipewire"):
        return None

    if want.isdigit():
        return int(want)

    devices = [
        (index, device)
        for index, device in enumerate(sd.query_devices())
        if device["max_input_channels"] > 0
    ]

    matches = [
        (index, device)
        for index, device in devices
        if device["name"].lower() == want.lower()
    ]

    matches = matches or [
        (index, device)
        for index, device in devices
        if want.lower() in device["name"].lower()
    ]

    if not matches:
        return None

    for index, device in matches:
        if device["hostapi"] == sd.default.hostapi:
            return index

    return matches[0][0]


def _save_recording(data):
    """Apply recording gain and save mono 16-bit PCM audio as a WAV file."""
    data = np.asarray(data, dtype=np.float32)

    if data.size == 0:
        return None

    level = float(np.percentile(np.abs(data), 99.5))

    if level > 50:
        gain = min(MAX_GAIN, TARGET_PEAK / level)
        data = np.clip(data * gain, -32768, 32767)

    data = data.astype(np.int16)

    folder = Path(tempfile.gettempdir()) / "caecus"
    folder.mkdir(exist_ok=True)

    path = folder / f"Recording {time.strftime('%b %d  %I.%M.%S %p')}.wav"

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(data.tobytes())

    return path


class Recorder:
    """Record audio from a selected PipeWire source or the system default."""

    def __init__(self):
        self._stream = None
        self._process = None
        self._raw_file = None
        self._raw_path = None
        self._chunks = []
        self._start = 0.0
        self._final = 0.0
        self.last_status = ""

    @property
    def recording(self):
        return self._stream is not None or self._process is not None

    def elapsed(self):
        if self.recording:
            return time.monotonic() - self._start
        return self._final

    def start(self):
        if self.recording:
            return

        self._chunks = []
        self.last_status = ""

        choice = load_choice()
        sources = _get_pipewire_sources()

        if choice in sources:
            self._start_pipewire(sources[choice])
        else:
            self._start_sounddevice()

        self._start = time.monotonic()

    def _start_pipewire(self, node_name):
        """Start recording directly from a named PipeWire input source."""
        if not shutil.which("pw-record"):
            raise RuntimeError("pw-record is not installed.")

        raw_file = tempfile.NamedTemporaryFile(
            prefix="caecus-",
            suffix=".raw",
            delete=False,
        )
        self._raw_file = raw_file
        self._raw_path = Path(raw_file.name)

        command = [
            "pw-record",
            "--raw",
            f"--target={node_name}",
            f"--rate={RATE}",
            "--channels=1",
            "--format=s16",
            "-",
        ]

        try:
            self._process = subprocess.Popen(
                command,
                stdout=raw_file,
                stderr=subprocess.PIPE,
            )
        except Exception:
            raw_file.close()
            self._raw_file = None
            self._raw_path.unlink(missing_ok=True)
            self._raw_path = None
            raise

        time.sleep(0.25)

        if self._process.poll() is not None:
            error = self._process.stderr.read().decode(
                "utf-8", errors="replace"
            )
            self._process = None
            raw_file.close()
            self._raw_file = None
            self._raw_path.unlink(missing_ok=True)
            self._raw_path = None
            raise RuntimeError(
                f"Could not record from {node_name}: {error.strip()}"
            )

    def _start_sounddevice(self):
        """Start recording through the existing PortAudio input route."""

        def callback(indata, frames, time_info, status):
            if status:
                self.last_status = str(status)
            self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=RATE,
            channels=1,
            dtype="int16",
            device=_pick_sounddevice(),
            callback=callback,
        )

        try:
            self._stream.start()
        except Exception:
            self._stream.close()
            self._stream = None
            raise

    def stop(self):
        """Stop recording and return the saved WAV file path."""
        self._final = time.monotonic() - self._start

        if self._process is not None:
            return self._stop_pipewire()

        if self._stream is not None:
            stream = self._stream
            self._stream = None

            try:
                stream.stop()
            finally:
                stream.close()

            if not self._chunks:
                return None

            data = np.concatenate(self._chunks).reshape(-1)
            return _save_recording(data)

        return None

    def _stop_pipewire(self):
        """Stop PipeWire recording and convert the raw audio to WAV."""
        process = self._process
        self._process = None

        try:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        finally:
            if self._raw_file is not None:
                self._raw_file.flush()
                self._raw_file.close()
                self._raw_file = None

        try:
            if self._raw_path is None or not self._raw_path.exists():
                return None

            data = np.fromfile(self._raw_path, dtype=np.int16)

            if data.size == 0:
                error = process.stderr.read().decode(
                    "utf-8", errors="replace"
                )
                if error.strip():
                    raise RuntimeError(error.strip())
                return None

            return _save_recording(data)
        finally:
            if self._raw_path is not None:
                self._raw_path.unlink(missing_ok=True)
                self._raw_path = None

    def cancel(self):
        """Cancel recording and discard its temporary audio."""
        self._chunks = []

        if self._process is not None:
            process = self._process
            self._process = None

            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

        if self._raw_file is not None:
            self._raw_file.close()
            self._raw_file = None

        if self._raw_path is not None:
            self._raw_path.unlink(missing_ok=True)
            self._raw_path = None

        if self._stream is not None:
            stream = self._stream
            self._stream = None

            try:
                stream.stop()
            finally:
                stream.close()


def cleanup_old(max_age_hours=24):
    """Delete old recordings from the application temporary folders."""
    cutoff = time.time() - max_age_hours * 3600
    temp = Path(tempfile.gettempdir())

    paths = [
        *(temp / "caecus").glob("*.wav"),
        *temp.glob("caecus-recording-*.wav"),
    ]

    for path in paths:
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass
