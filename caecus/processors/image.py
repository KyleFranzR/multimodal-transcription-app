import os
from pathlib import Path
from PIL import Image, ImageOps
import pytesseract

import config


class ImageProcessor:
    def __init__(self):
        self.supported_extensions = {".png", ".jpg", ".jpeg", ".bmp"}
        self._configure_tesseract()

    def _configure_tesseract(self):
        if config.TESSERACT_CMD and config.TESSERACT_CMD.exists():
            pytesseract.pytesseract.tesseract_cmd = str(config.TESSERACT_CMD)
            if config.TESSDATA_PREFIX and config.TESSDATA_PREFIX.exists():
                os.environ["TESSDATA_PREFIX"] = str(config.TESSDATA_PREFIX)

    def process(self, file_path: str, progress_callback=None, is_cancelled=None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        ext = path.suffix.lower()
        if ext not in self.supported_extensions:
            raise ValueError(f"Unsupported image extension: {ext}")

        if not config.TESSERACT_CMD or not config.TESSERACT_CMD.exists():
            raise RuntimeError(
                "Tesseract executable not found. Please install Tesseract-OCR or place "
                "tesseract.exe inside 'caecus/bin/Tesseract-OCR/'."
            )

        if is_cancelled and is_cancelled():
            return ""

        if progress_callback:
            progress_callback(0.2)

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)  # honour camera rotation
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                white = Image.new("RGBA", img.size, (255, 255, 255, 255))
                white.alpha_composite(img)  # transparent pixels become white, not black
                img = white
            gray = img.convert("L")
            longest = max(gray.size)
            if longest < 1000:  # small text OCRs badly; enlarge
                gray = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
            elif longest > 3000:
                gray.thumbnail((3000, 3000), Image.Resampling.BILINEAR)

            if is_cancelled and is_cancelled():
                return ""

            text = pytesseract.image_to_string(gray)

        if progress_callback:
            progress_callback(1.0)

        return text.strip()


if __name__ == "__main__":
    processor = ImageProcessor()
    print("✓ ImageProcessor ready.")