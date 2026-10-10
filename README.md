# multimodal-transcription-app
Transcribes spoken speech and files such as documents, image, video, and audio.

---

## Features

* **Real-Time Audio Streaming:** Low-latency live microphone transcription via `sherpa-onnx`.
* **Multimodal File Processing:** Supports documents (`.docx`, `.pdf`), images (`.png`, `.jpg`, `.bmp` via Tesseract OCR), audio files (`.wav`, `.mp3`), and video files (`.mp4`, `.mov`).
* **Fully Offline & Edge-Native:** Designed for local inference with zero cloud dependency.

---

## Project Structure

```text
multimodal-transcription-app/
├── caecus/
│   ├── bin/                    # Platform binaries / Tesseract OCR executables
│   ├── gui/
│   │   └── app.py              # Touchscreen CustomTkinter GUI
│   ├── models/                 # Sherpa-ONNX ASR model directories (.onnx)
│   ├── processors/             # File ingestion modules
│   │   ├── audio.py
│   │   ├── document.py
│   │   ├── image.py
│   │   └── video.py
│   ├── services/               # Core engine services
│   │   ├── engine.py           # Sherpa-ONNX ASR engine manager
│   │   └── recorder.py         # Audio stream recorder
│   ├── storage/                # Processing cache & temporary storage
│   ├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── config.py               # Centralized pathing & runtime configurations
│   └── main.py                 # Primary application entry point
├── storage/                    # Root-level data/media storage
├── .gitignore
├── LICENSE
├── pyproject.toml              # Build & dependency metadata
└── README.md                   # Documentation
```

---

## System Requirements

* **Hardware:** Raspberry Pi 5 (or x86_64 Windows/Linux host for development).
* **OS:** Raspberry Pi OS 64-bit (Bookworm) or Linux / Windows.
* **Python:** `>= 3.10`

---

## External Binaries & Models Setup

Because large binaries and models are excluded from version control, you must place them inside the project directories before running the app.

### 1. Tesseract OCR

* Download the Tesseract binaries for your operating system (or install via `sudo apt install tesseract-ocr` on Linux/Raspberry Pi OS).
* Place the folder inside `caecus/bin/` so the path resolves to:

```text
caecus/bin/Tesseract-OCR/
```

### 2. Sherpa-ONNX Speech Model

1. Download [sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8.tar.bz2](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8.tar.bz2).
2. Extract the archive into `caecus/models/` so the path looks like this:

```text
caecus/models/sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8/
```

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KyleFranzR/caecus.git
   cd caecus
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the project along with its dependencies using `pip`:**
   ```bash
   pip install .
   ```

   *For editable development mode:*
   ```bash
   pip install -e .
   ```

---

## Usage

You can launch the application directly using Python module execution:

```bash
python -m caecus.main
```

Or via the installed CLI executable entry point:

```bash
caecus
```

---

## Configuration

Settings such as audio sample rates (`16000 Hz`), chunk sizing, and binary pathing logic are centralized in `caecus/config.py`.

* **Windows:** Dynamically checks `caecus/bin/Tesseract-OCR/tesseract.exe` or system installations (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
* **Linux / Raspberry Pi OS:** Uses system paths (`/usr/bin/tesseract`) or project-local binaries inside `caecus/bin/`.

---

## License

This project is licensed under the [MIT License](LICENSE).