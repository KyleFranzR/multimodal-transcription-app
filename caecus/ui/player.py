import shutil
import subprocess
import time

import numpy as np

LATENCY = 0.35  # ffplay start-up delay; keeps the slider roughly in step with the sound


def fmt_time(seconds):
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def decode_overview(path, rate=4000):
    """Decode to mono at a low rate with ffmpeg: gives the duration and data for the waveform."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
         "-f", "s16le", "-"], capture_output=True, timeout=180)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(proc.stderr.decode(errors="ignore").strip()[:120] or "could not decode the audio")
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0, rate


def compute_peaks(samples, bins=56):
    if len(samples) == 0:
        return [0.1] * bins
    peaks = [float(np.sqrt(np.mean(c ** 2))) if len(c) else 0.0 for c in np.array_split(samples, bins)]
    top = max(peaks) or 1.0
    return [max(0.08, p / top) for p in peaks]


def _has_video(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(path)], capture_output=True, timeout=15).stdout
        return bool(out.strip())
    except Exception:
        return False


def _seekable_audio(path):
    """ffplay seeks to the nearest *video keyframe* when the file has a video stream, so the sound
    lands up to a few seconds off the slider. A plain audio copy seeks exactly."""
    import hashlib
    import os
    import tempfile
    path = str(path)
    if not _has_video(path):
        return path
    folder = os.path.join(tempfile.gettempdir(), "caecus_audio")
    os.makedirs(folder, exist_ok=True)
    now = time.time()
    for name in os.listdir(folder):  # drop copies older than a day
        try:
            if now - os.path.getmtime(os.path.join(folder, name)) > 86400:
                os.remove(os.path.join(folder, name))
        except OSError:
            pass
    st = os.stat(path)
    key = hashlib.sha1(f"{path}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:16]
    out = os.path.join(folder, key + ".wav")
    if not os.path.exists(out):
        tmp = out + ".part.wav"
        proc = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", path, "-vn", "-ac", "1",
                               "-ar", "22050", "-c:a", "pcm_s16le", tmp], capture_output=True, timeout=300)
        if proc.returncode != 0:
            return path  # no audio track, or ffmpeg failed: play the original
        os.replace(tmp, out)
    return out


class AudioPlayer:
    """Plays through ffplay (the system audio server), like the old preview did."""

    def __init__(self, path, duration, video=False):
        if shutil.which("ffplay") is None:
            raise RuntimeError("ffplay is not installed (install FFmpeg and add it to PATH)")
        self.path, self.duration, self.video = str(path), duration, video
        self.play_path = self.path if video else _seekable_audio(self.path)
        self._proc, self._start_pos, self._start_time, self._pos = None, 0.0, 0.0, 0.0
        self.failed = False 

    @property
    def playing(self):
        return self._proc is not None and self._proc.poll() is None

    def position(self):
        if self._proc is not None:
            if self._proc.poll() is None:
                elapsed = max(0.0, time.monotonic() - self._start_time - LATENCY)
                return min(self.duration, self._start_pos + elapsed)
            ran_for = time.monotonic() - self._start_time
            self.failed = self._proc.returncode != 0 or ran_for < 0.5
            self._pos = self._start_pos if self.failed else self.duration
            self._proc = None
        return self._pos

    def play(self):
        self.pause()
        start = 0.0 if self._pos >= self.duration - 0.05 else self._pos
        self.failed = False
        cmd = ["ffplay"] + ([] if self.video else ["-nodisp"]) + [
            "-autoexit", "-loglevel", "quiet", "-ss", f"{start:.2f}", self.play_path]
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._start_pos, self._start_time = start, time.monotonic()

    def pause(self):
        if self._proc is not None:
            self._pos = self.position()
            if self._proc is not None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None

    def seek(self, seconds):
        was_playing = self.playing
        self.pause()
        self._pos = max(0.0, min(seconds, self.duration))
        if was_playing:
            self.play()

    def close(self):
        self.pause()
