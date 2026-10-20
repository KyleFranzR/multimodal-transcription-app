import sys
from pathlib import Path
import soundfile as sf
import sherpa_onnx


class ASRService:
    def __init__(self, model_dir_name: str = "sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8"):
        # Points directly to caecus/models/<model_dir_name>
        self.package_root = Path(__file__).resolve().parents[1]
        self.model_dir = self.package_root / "models" / model_dir_name

        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found at: {self.model_dir}")

        # Find transducer ONNX files and tokens file dynamically
        encoder_path = self._find_file(["encoder.int8.onnx", "encoder.onnx", "*encoder*.onnx"])
        decoder_path = self._find_file(["decoder.int8.onnx", "decoder.onnx", "*decoder*.onnx"])
        joiner_path = self._find_file(["joiner.int8.onnx", "joiner.onnx", "*joiner*.onnx"])
        tokens_path = self.model_dir / "tokens.txt"

        if not tokens_path.exists():
            raise FileNotFoundError(f"Tokens file missing: {tokens_path}")

        # Initialize directly using sherpa-onnx's verified from_transducer method
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=str(encoder_path),
            decoder=str(decoder_path),
            joiner=str(joiner_path),
            tokens=str(tokens_path),
            num_threads=2,
            provider="cpu",
            decoding_method="greedy_search",
        )

    def _find_file(self, patterns: list) -> Path:
        """Helper to find matching ONNX model files regardless of exact filename."""
        for pattern in patterns:
            matches = list(self.model_dir.glob(pattern))
            if matches:
                return matches[0]
        raise FileNotFoundError(f"Could not find matching file pattern {patterns} in {self.model_dir}")

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribes a WAV audio file to plain text."""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        samples, sample_rate = sf.read(str(audio_file), dtype="float32")

        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)

        # Append tail padding to let the model finish decoding
        tail_padding = [0] * int(sample_rate * 0.5)
        stream.accept_waveform(sample_rate, tail_padding)
        stream.input_finished()

        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)

        return self.recognizer.get_result(stream).strip()


if __name__ == "__main__":
    print("Initializing ASR Engine with FastConformer Transducer...")
    try:
        asr = ASRService()
        print("ASR Engine loaded and initialized successfully.")

        if len(sys.argv) > 1:
            test_wav = sys.argv[1]
            print(f"\nTranscribing test file: {test_wav}")
            result = asr.transcribe_file(test_wav)
            print("-" * 40)
            print(result)
            print("-" * 40)
    except Exception as e:
        print(f"\nInitialization failed: {e}")