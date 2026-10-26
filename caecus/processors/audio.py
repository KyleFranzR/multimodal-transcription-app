from pathlib import Path
import librosa

import config

import numpy as np

class AudioProcessor:
    def __init__(self, asr_service=None):
        self.supported_extensions = {".wav", ".mp3", ".ogg"}
        self.asr_service = asr_service

    def process(self, file_path: str, progress_callback=None, is_cancelled=None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        ext = path.suffix.lower()
        if ext not in self.supported_extensions:
            raise ValueError(f"Unsupported audio extension: {ext}")

        if not self.asr_service:
            raise RuntimeError("ASRService instance must be provided to AudioProcessor.")

        audio_data, _ = librosa.load(str(path), sr=config.SAMPLE_RATE, mono=True)
        total_samples = len(audio_data)

        if total_samples == 0:
            return ""

        stream = self.asr_service.recognizer.create_stream()

        for offset in range(0, total_samples, config.AUDIO_CHUNK_SIZE):
            if is_cancelled and is_cancelled():
                return ""

            chunk = audio_data[offset : offset + config.AUDIO_CHUNK_SIZE]
            stream.accept_waveform(config.SAMPLE_RATE, chunk)

            while self.asr_service.recognizer.is_ready(stream):
                self.asr_service.recognizer.decode_stream(stream)

            if progress_callback:
                processed_ratio = min(1.0, (offset + len(chunk)) / total_samples)
                progress_callback(processed_ratio)

        # Flush: need silence to get last word.
        tail = np.zeros(int(1.0 * config.SAMPLE_RATE), dtype=np.float32)
        stream.accept_waveform(config.SAMPLE_RATE, tail)
        stream.input_finished()
        while self.asr_service.recognizer.is_ready(stream):
            self.asr_service.recognizer.decode_stream(stream)

        return self.asr_service.recognizer.get_result(stream).strip()