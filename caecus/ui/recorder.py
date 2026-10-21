import json
import os
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

RATE = 16000  # 16 kHz mono
TARGET_PEAK = 0.8 * 32767  # gaano kalakas gagawin ang recording
MAX_GAIN = 30.0  # limitasyon para hindi lumakas ang ingay kapag halos tahimik
SETTINGS = Path.home() / ".caecus_settings.json"
_HIDDEN = ("sound mapper", "primary sound", "stereo mix", "midi")


def input_devices():
    """Mic names to show in the dropdown (isang beses bawat pangalan)."""
    host = sd.default.hostapi
    devs = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
    devs.sort(key=lambda d: d["hostapi"] != host)
    names = []
    for d in devs:
        name = d["name"]
        if name not in names and not any(h in name.lower() for h in _HIDDEN):
            names.append(name)
    return names


def load_choice():
    """CAECUS_MIC (index or name) wins; otherwise the saved dropdown choice; '' = system default."""
    want = os.environ.get("CAECUS_MIC", "").strip()
    if want:
        return want
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8")).get("mic", "")
    except Exception:
        return ""


def save_choice(name):
    try:
        SETTINGS.write_text(json.dumps({"mic": name}), encoding="utf-8")
    except OSError:
        pass


def _pick_device():
    want = load_choice()
    if not want:
        return None  # default input ng Windows
    if want.isdigit():
        return int(want)
    inputs = [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    matches = [(i, d) for i, d in inputs if d["name"].lower() == want.lower()]
    matches = matches or [(i, d) for i, d in inputs if want.lower() in d["name"].lower()]
    if not matches:
        return None  # naka-unplug ang mic: bumalik sa default
    for i, d in matches:
        if d["hostapi"] == sd.default.hostapi:
            return i
    return matches[0][0]


class Recorder:
    """Records from the chosen (or default) microphone into a WAV file."""

    def __init__(self):
        self._stream = None
        self._chunks = []
        self._start = 0.0
        self._final = 0.0
        self.last_status = ""

    @property
    def recording(self):
        return self._stream is not None

    def elapsed(self):
        return time.monotonic() - self._start if self._stream is not None else self._final

    def start(self):
        if self._stream is not None:
            return
        self._chunks, self.last_status = [], ""

        def callback(indata, frames, time_info, status):
            if status:
                self.last_status = str(status)
            self._chunks.append(indata.copy())

        self._stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16",
                                      device=_pick_device(), callback=callback)
        self._stream.start()
        self._start = time.monotonic()

    def stop(self):
        """Stop and save. Returns the WAV path, or None if nothing was recorded."""
        stream, self._stream = self._stream, None
        if stream is None:
            return None
        self._final = time.monotonic() - self._start
        try:
            stream.stop()
        finally:
            stream.close()
        if not self._chunks:
            return None
        data = np.concatenate(self._chunks).astype(np.float32)
        level = float(np.percentile(np.abs(data), 99.5))  # hindi apektado ng isang biglang spike
        if level > 50:  # hindi tahimik
            data = np.clip(data * min(MAX_GAIN, TARGET_PEAK / level), -32768, 32767)
        data = data.astype(np.int16)
        path = Path(tempfile.gettempdir()) / f"caecus-recording-{time.strftime('%Y%m%d-%H%M%S')}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(data.tobytes())
        return path

    def cancel(self):
        stream, self._stream = self._stream, None
        self._chunks = []
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()

def cleanup_old(max_age_hours=24):
        """Delete caecus-recording-*.wav in the temp folder that are older than max_age_hours."""
        cutoff = time.time() - max_age_hours * 3600
        for path in Path(tempfile.gettempdir()).glob("caecus-recording-*.wav"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass  # ginagamit pa o walang permiso: laktawan   