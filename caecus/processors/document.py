import os
from io import BytesIO
from pathlib import Path
import docx
import pypdf
import pytesseract
from PIL import Image

# Cap OpenMP threads on Raspberry Pi 5 to keep 2 cores open for the GUI
os.environ["OMP_THREAD_LIMIT"] = "2"


class DocumentProcessor:
    def __init__(self):
        self.supported_extensions = {".docx", ".pdf", ".txt"}

    def process(self, file_path: str, progress_callback=None, is_cancelled=None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = path.suffix.lower()
        if ext == ".txt":
            return self._extract_txt(path, progress_callback, is_cancelled)
        elif ext == ".docx":
            return self._extract_docx(path, progress_callback, is_cancelled)
        elif ext == ".pdf":
            return self._extract_pdf(path, progress_callback, is_cancelled)
        else:
            raise ValueError(f"Unsupported document extension: {ext}")

    def _extract_txt(self, path: Path, progress_callback, is_cancelled) -> str:
        """Lightweight native text extraction for .txt files."""
        if is_cancelled and is_cancelled():
            return ""

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
        except Exception as e:
            raise RuntimeError(f"Failed to read text file: {e}")

        if progress_callback:
            progress_callback(1.0)

        return content

    def _extract_docx(self, path: Path, progress_callback, is_cancelled) -> str:
        doc = docx.Document(path)
        paragraphs = doc.paragraphs
        total = len(paragraphs)
        if total == 0:
            return ""

        extracted = []
        step = max(1, total // 50)

        for i, p in enumerate(paragraphs):
            if is_cancelled and is_cancelled():
                return ""

            text = p.text.strip()
            if text:
                extracted.append(text)

            if progress_callback and (i % step == 0 or i == total - 1):
                progress_callback((i + 1) / total)

        return "\n\n".join(extracted)

    def _extract_pdf(self, path: Path, progress_callback, is_cancelled) -> str:
        reader = pypdf.PdfReader(path)
        total_pages = len(reader.pages)
        if total_pages == 0:
            return ""

        text_pages = []
        step = max(1, total_pages // 50)

        for i, page in enumerate(reader.pages):
            if is_cancelled and is_cancelled():
                return ""

            extracted = page.extract_text()

            # Fast OCR fallback tuned specifically for Pi 5 ARM CPU
            if not extracted or not extracted.strip():
                ocr_text = []
                for img_obj in page.images:
                    if is_cancelled and is_cancelled():
                        return ""
                    try:
                        img = Image.open(BytesIO(img_obj.data))

                        # 1. Downscale to max 1200px (Saves massive CPU cycles on Pi 5)
                        if max(img.size) > 1200:
                            img.thumbnail((1200, 1200), Image.Resampling.BILINEAR)

                        # 2. Convert to Grayscale
                        if img.mode != "L":
                            img = img.convert("L")

                        # 3. Fast Tesseract flags for Pi 5
                        txt = pytesseract.image_to_string(
                            img, config="--oem 1 --psm 3 -c tessedit_do_invert=0"
                        ).strip()

                        if txt:
                            ocr_text.append(txt)
                    except Exception:
                        pass
                extracted = "\n".join(ocr_text)

            if extracted and extracted.strip():
                text_pages.append(extracted.strip())

            if progress_callback and (i % step == 0 or i == total_pages - 1):
                progress_callback((i + 1) / total_pages)

        return "\n\n".join(text_pages)