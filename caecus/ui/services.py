"""Bridge between the UI and the processors (contract: process(path, progress_callback, is_cancelled) -> str)."""
import sys
import threading
from pathlib import Path

# The processors still do `import config`; make that resolvable without touching them.
_PKG_DIR = str(Path(__file__).resolve().parents[1])
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)


class Transcriber:
    def __init__(self):
        self._processors = {}
        self.asr = None
        self.asr_state = "idle"  # idle | loading | ready | error
        self.asr_error = ""

    def start_loading(self):
        if self.asr_state != "idle":
            return
        self.asr_state = "loading"
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            from caecus.services.engine import ASRService
            from caecus.processors.audio import AudioProcessor
            from caecus.processors.video import VideoProcessor
            self.asr = ASRService()
            self._processors["audio"] = AudioProcessor(asr_service=self.asr)
            self._processors["video"] = VideoProcessor(asr_service=self.asr)
            self.asr_state = "ready"
        except Exception as exc:
            self.asr_error = str(exc)
            self.asr_state = "error"

    def _get(self, kind):
        if kind in ("audio", "video"):
            if self.asr_state != "ready":
                raise RuntimeError("The speech engine is not ready")
            return self._processors[kind]
        if kind not in self._processors:
            if kind == "document":
                from caecus.processors.document import DocumentProcessor
                self._processors[kind] = DocumentProcessor()
            elif kind == "image":
                from caecus.processors.image import ImageProcessor
                self._processors[kind] = ImageProcessor()
            else:
                raise ValueError(f"Unsupported file type: {kind}")
        return self._processors[kind]

    def convert(self, kind, path, progress, is_cancelled):
        return self._get(kind).process(path, progress_callback=progress, is_cancelled=is_cancelled)
