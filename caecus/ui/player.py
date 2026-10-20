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


class AudioPlayer:
    """Plays through ffplay (the system audio server), like the old preview did."""

    def __init__(self, path, duration):
        if shutil.which("ffplay") is None:
            raise RuntimeError("ffplay is not installed (sudo apt install ffmpeg)")
        self.path, self.duration = str(path), duration
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
        self._proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-ss", f"{start:.2f}", self.path],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
