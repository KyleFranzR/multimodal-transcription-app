import queue
import sounddevice as sd
import numpy as np


class AudioRecorderService:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function invoked by sounddevice for each audio block."""
        if status:
            print(f"Audio stream status warning: {status}", flush=True)
        # Convert float32 array to 1D continuous numpy array and queue it
        self.audio_queue.put(indata.copy().flatten())

    def start_recording(self):
        """Starts capturing microphone input in a non-blocking background stream."""
        if self.is_recording:
            return

        self.is_recording = True
        # Clear any stale audio data from previous sessions
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
        )
        self._stream.start()

    def stop_recording(self):
        """Stops capturing microphone input."""
        if not self.is_recording:
            return

        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_audio_chunk(self):
        """Retrieves the next queued audio numpy array chunk, or None if queue is empty."""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None


if __name__ == "__main__":
    import time

    print("Testing AudioRecorderService...")
    recorder = AudioRecorderService()
    print("Starting 3-second microphone test recording...")
    recorder.start_recording()

    for i in range(30):
        chunk = recorder.get_audio_chunk()
        if chunk is not None:
            print(f"Captured audio chunk with shape: {chunk.shape}")
        time.sleep(0.1)

    recorder.stop_recording()
    print("Mic recorder test complete!")