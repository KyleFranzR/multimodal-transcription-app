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
│   │   └── preview_dialog.py
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

4. **Install the system packages (not installed by pip):**

   *Raspberry Pi:*
```bash
   sudo apt update
   sudo apt install ffmpeg tesseract-ocr libportaudio2 libsndfile1 python3-tk fonts-dejavu
```

   *Windows:*
```bash
   winget install Gyan.FFmpeg
   winget install UB-Mannheim.TesseractOCR
```

   These are needed for audio/video preview (FFmpeg), reading text from images (Tesseract),
   microphone recording (`libportaudio2`) and the braille characters (`fonts-dejavu`).
   On Windows, close and reopen the terminal afterwards.

5. **Run the app: (with New UI)**
```bash
   python -m caecus.ui.app
```

6. **Microphone (Speak option):**

   On the Import screen, pick your microphone from the dropdown beside *Transcribe speech*.
   Leave it on *System default* to use the system's default input device.

---

## Usage

Run these from the project root with the virtual environment active (after `pip install -e .`). Both interfaces start in fullscreen kiosk mode; press `Ctrl+Alt+Q` to exit.

| Interface | Command | Notes |
|---|---|---|
| **New GUI** (guided Attach, Preview, Edit text flow, follows the Figma design) | `python -m caecus.ui.app` | In development |
| **Old GUI** (single screen with live microphone transcription) | `python -m caecus.main` | Also available as the `caecus` command |

To test in a window instead of fullscreen, set `CAECUS_GEOMETRY`, for example `CAECUS_GEOMETRY=1024x600 python -m caecus.ui.app`.

### Feature status

| Feature | Old GUI | New GUI |
|---|---|---|
| Live microphone transcription | Yes | Planned |
| Image, document and audio files | Yes | Yes |
| Video files | Yes | Yes (still-frame preview, playback planned) |
| Preview before converting | Side panel | Full-screen step |
| Copy and save the text | No | Yes |
| Typed text input | No | Yes |
| Braille output | Placeholder | Planned |

Audio preview in the new GUI plays through `ffplay` (`sudo apt install ffmpeg` on Raspberry Pi OS).

---

## Configuration

Settings such as audio sample rates (`16000 Hz`), chunk sizing, and binary pathing logic are centralized in `caecus/config.py`.

* **Windows:** Dynamically checks `caecus/bin/Tesseract-OCR/tesseract.exe` or system installations (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
* **Linux / Raspberry Pi OS:** Uses system paths (`/usr/bin/tesseract`) or project-local binaries inside `caecus/bin/`.

---

## License

This project is licensed under the [MIT License](LICENSE).