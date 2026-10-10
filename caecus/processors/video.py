import os
import tempfile
from pathlib import Path
import librosa
from moviepy import VideoFileClip

import config

class VideoProcessor:
    def __init__(self, asr_service=None):
        self.supported_extensions = {".mp4", ".mov", ".avi", ".mkv"}
        self.asr_service = asr_service

    def process(self, file_path: str, progress_callback=None, is_cancelled=None) -> str:
        path = Path(file_path)
        if not path.exists() or path.suffix.lower() not in self.supported_extensions:
            raise ValueError(f"Invalid or unsupported video file: {file_path}")

        if not self.asr_service:
            raise RuntimeError("ASRService instance must be provided to VideoProcessor.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_wav = tmp.name

        try:
            with VideoFileClip(str(path)) as clip:
                if clip.audio is None:
                    return ""
                clip.audio.write_audiofile(
                    temp_wav, fps=config.SAMPLE_RATE, nbytes=2, codec="pcm_s16le", logger=None
                )

            if is_cancelled and is_cancelled():
                return ""

            audio_data, _ = librosa.load(temp_wav, sr=config.SAMPLE_RATE, mono=True)
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
                    progress_callback(min(1.0, (offset + len(chunk)) / total_samples))

            return self.asr_service.recognizer.get_result(stream).strip()

        finally:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)