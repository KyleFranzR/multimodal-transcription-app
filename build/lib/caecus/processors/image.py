import os
from pathlib import Path
from PIL import Image
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
            rgb_img = img.convert("RGB")

            if is_cancelled and is_cancelled():
                return ""

            text = pytesseract.image_to_string(rgb_img)

        if progress_callback:
            progress_callback(1.0)

        return text.strip()


if __name__ == "__main__":
    processor = ImageProcessor()
    print("✓ ImageProcessor ready.")