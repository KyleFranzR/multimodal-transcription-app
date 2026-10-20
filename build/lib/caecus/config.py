import sys
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).resolve().parent

# Check potential package locations
if (ROOT_DIR / "caecus").exists():
    PACKAGE_DIR = ROOT_DIR / "caecus"
else:
    PACKAGE_DIR = ROOT_DIR

# Audio Settings
SAMPLE_RATE = 16000
AUDIO_CHUNK_SIZE = 160000  # 10 seconds at 16kHz

# Tesseract OCR Paths
IS_WINDOWS = sys.platform.startswith("win")
TESSERACT_BINARY_NAME = "tesseract.exe" if IS_WINDOWS else "tesseract"

def find_tesseract():
    # 1. Search recursively inside project bin/ folder
    bin_dir = PACKAGE_DIR / "bin"
    if bin_dir.exists():
        matches = list(bin_dir.rglob(TESSERACT_BINARY_NAME))
        if matches:
            exe_path = matches[0]
            # Check for tessdata relative to the found binary
            tessdata = exe_path.parent / "tessdata"
            if not tessdata.exists():
                tessdata = bin_dir / "Tesseract-OCR" / "tessdata"
            return exe_path, tessdata

    # 2. Check standard Windows system installation
    if IS_WINDOWS:
        sys_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if sys_path.exists():
            return sys_path, sys_path.parent / "tessdata"
        
        sys_path_x86 = Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")
        if sys_path_x86.exists():
            return sys_path_x86, sys_path_x86.parent / "tessdata"
    else:
        # Standard Linux / Pi path
        sys_path = Path("/usr/bin/tesseract")
        if sys_path.exists():
            return sys_path, Path("/usr/share/tesseract-ocr/4.00/tessdata")

    return None, None

TESSERACT_CMD, TESSDATA_PREFIX = find_tesseract()