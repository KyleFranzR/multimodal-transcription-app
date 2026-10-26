import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import sherpa_onnx


class ASRService:
    def __init__(
        self,
        model_dir_name: str = "sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8",
    ):
        self.package_root = Path(__file__).resolve().parents[1]
        self.model_dir = self.package_root / "models" / model_dir_name

        if not self.model_dir.is_dir():
            raise FileNotFoundError(
                f"Model directory not found at: {self.model_dir}"
            )

        encoder_path = self._find_file(
            ["encoder.int8.onnx", "encoder.onnx", "*encoder*.onnx"]
        )

        if model_dir_name == "sherpa-onnx-streaming-zipformer-fil-en":
            decoder_path = self.model_dir / "decoder.onnx"
        else:
            decoder_path = self._find_file(
                ["decoder.int8.onnx", "decoder.onnx", "*decoder*.onnx"]
            )

        joiner_path = self._find_file(
            ["joiner.int8.onnx", "joiner.onnx", "*joiner*.onnx"]
        )
        tokens_path = self.model_dir / "tokens.txt"

        for file_path in (
            encoder_path,
            decoder_path,
            joiner_path,
            tokens_path,
        ):
            if not file_path.is_file():
                raise FileNotFoundError(f"Required model file missing: {file_path}")

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=str(encoder_path),
            decoder=str(decoder_path),
            joiner=str(joiner_path),
            tokens=str(tokens_path),
            num_threads=4 if model_dir_name == "sherpa-onnx-streaming-zipformer-fil-en" else 2,
            sample_rate=16000,
            feature_dim=80,
            provider="cpu",
            decoding_method="modified_beam_search",
            enable_endpoint_detection=True,
        )

    def _find_file(self, patterns: list) -> Path:
        for pattern in patterns:
            matches = list(self.model_dir.glob(pattern))
            if matches:
                return matches[0]

        raise FileNotFoundError(
            f"Could not find matching file pattern {patterns} "
            f"in {self.model_dir}"
        )

    def finish_stream(self, stream, sample_rate: int = 16000) -> str:
        """Flush the final audio frames and return the completed transcript."""
        tail_padding = np.zeros(
            int(sample_rate * 0.5),
            dtype=np.float32,
        )
        stream.accept_waveform(sample_rate, tail_padding)
        stream.input_finished()

        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)

        result = self.recognizer.get_result(stream)
        text = result.text if hasattr(result, "text") else str(result)
        return text.strip()

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe a WAV file."""
        audio_file = Path(audio_path)

        if not audio_file.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        samples, sample_rate = sf.read(str(audio_file), dtype="float32")

        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        if sample_rate != 16000:
            raise ValueError(
                f"Expected 16000 Hz audio, received {sample_rate} Hz"
            )

        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)

        return self.finish_stream(stream, sample_rate)


if __name__ == "__main__":
    print("Initializing ASR Engine...")
    try:
        model_name = (
            "sherpa-onnx-streaming-zipformer-fil-en"
            if len(sys.argv) < 2
            else sys.argv[1]
        )
        asr = ASRService(model_dir_name=model_name)
        print(f"ASR Engine loaded successfully: {model_name}")

        if len(sys.argv) > 2:
            test_wav = sys.argv[2]
            print(f"\nTranscribing: {test_wav}")
            print(asr.transcribe_file(test_wav))

    except Exception as exc:
        print(f"\nInitialization failed: {exc}")
        raise
