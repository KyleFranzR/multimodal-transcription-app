import os
import sys
import threading
import time
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog

import config
from caecus.services.engine import ASRService
from caecus.services.recorder import AudioRecorderService
from caecus.processors.document import DocumentProcessor
from caecus.processors.image import ImageProcessor
from caecus.processors.audio import AudioProcessor
from caecus.processors.video import VideoProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class CaecusApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Caecus - Offline Multimodal Transcription")
        self.geometry("800x480")  # Standard Pi LCD touch resolution
        self.minsize(600, 400)

        # Optional: Uncomment line below for borderless touchscreen Kiosk mode on Pi
        # self.attributes("-fullscreen", True)

        # Core Services
        self.asr = None
        self.recorder = AudioRecorderService(sample_rate=config.SAMPLE_RATE)

        # Processors
        self.doc_processor = DocumentProcessor()
        self.img_processor = ImageProcessor()
        self.audio_processor = None
        self.video_processor = None

        # State Variables
        self.is_transcribing = False
        self.cancel_event = threading.Event()
        self._last_touch_y = 0

        self._setup_ui()

        # Load ASR Engine in background to prevent UI freeze on boot
        threading.Thread(target=self._init_asr_engine, daemon=True).start()

    def _setup_ui(self):
        # Header / Status Frame
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(padx=15, pady=(15, 10), fill="x")

        self.title_label = ctk.CTkLabel(
            self.header_frame, text="Caecus", font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(side="left", padx=15, pady=12)

        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="Status: Initializing ASR Engine...",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="orange",
        )
        self.status_label.pack(side="right", padx=15, pady=12)

        # Main Text Display Area with Touch Drag Scrolling
        self.textbox = ctk.CTkTextbox(
            self, font=ctk.CTkFont(size=18), wrap="word", activate_scrollbars=True
        )
        self.textbox.pack(padx=15, pady=8, fill="both", expand=True)

        # Bind touchscreen drag gesture to scroll text
        self.textbox.bind("<Button-1>", self._start_touch_scroll, add="+")
        self.textbox.bind("<B1-Motion>", self._touch_scroll, add="+")

        # Progress Indicator Frame
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(padx=15, pady=(0, 5), fill="x")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=16)
        self.progress_bar.pack(fill="x", padx=5)
        self.progress_bar.set(0)

        # Touch-Optimized Controls Frame (Height: 50px, Font: 16pt)
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.pack(padx=15, pady=(5, 15), fill="x")

        self.toggle_btn = ctk.CTkButton(
            self.controls_frame,
            text="Start Listening",
            command=self.toggle_mic_transcription,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.toggle_btn.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.file_btn = ctk.CTkButton(
            self.controls_frame,
            text="Import File",
            command=self.open_file_dialog,
            state="disabled",
            fg_color="#1f538d",
            hover_color="#14375e",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.file_btn.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.cancel_btn = ctk.CTkButton(
            self.controls_frame,
            text="Cancel",
            command=self.cancel_file_processing,
            fg_color="darkred",
            hover_color="#8B0000",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
        )

        self.clear_btn = ctk.CTkButton(
            self.controls_frame,
            text="Clear Text",
            command=self.clear_text,
            fg_color="gray",
            hover_color="#404040",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.clear_btn.pack(side="right", padx=10, pady=10)

    # --- Touch Gesture Scroll Handlers ---
    def _start_touch_scroll(self, event):
        self._last_touch_y = event.y

    def _touch_scroll(self, event):
        if hasattr(self, "_last_touch_y"):
            delta = self._last_touch_y - event.y
            if abs(delta) > 5:
                self.textbox.yview_scroll(int(delta / 10), "units")
                self._last_touch_y = event.y

    # --- Engine Initialization ---
    def _init_asr_engine(self):
        try:
            self.asr = ASRService()
            self.audio_processor = AudioProcessor(asr_service=self.asr)
            self.video_processor = VideoProcessor(asr_service=self.asr)
            self.after(0, self._on_engine_ready)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_engine_error(msg))

    def _on_engine_ready(self):
        self.status_label.configure(text="Status: Ready", text_color="green")
        self.toggle_btn.configure(state="normal")
        self.file_btn.configure(state="normal")

    def _on_engine_error(self, err_msg: str):
        self.status_label.configure(text="Status: Engine Error", text_color="red")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", f"Error initializing ASR Engine:\n{err_msg}")

    # --- Live Mic Stream Logic ---
    def toggle_mic_transcription(self):
        if not self.is_transcribing:
            self.start_mic_transcription()
        else:
            self.stop_mic_transcription()

    def start_mic_transcription(self):
        self.is_transcribing = True
        self.toggle_btn.configure(text="Stop Listening", fg_color="red", hover_color="darkred")
        self.file_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Listening...", text_color="#0066FF")

        self.recorder.start_recording()
        threading.Thread(target=self._mic_worker, daemon=True).start()

    def stop_mic_transcription(self):
        self.is_transcribing = False
        self.recorder.stop_recording()
        self.toggle_btn.configure(text="Start Listening", fg_color="green", hover_color="darkgreen")
        self.file_btn.configure(state="normal")
        self.status_label.configure(text="Status: Ready", text_color="green")

    def _mic_worker(self):
        stream = self.asr.recognizer.create_stream()
        last_text = ""

        while self.is_transcribing:
            chunk = self.recorder.get_audio_chunk()
            if chunk is not None:
                stream.accept_waveform(config.SAMPLE_RATE, chunk)

                while self.asr.recognizer.is_ready(stream):
                    self.asr.recognizer.decode_stream(stream)

                text = self.asr.recognizer.get_result(stream).strip()
                if text and text != last_text:
                    cleaned_text = " ".join(text.split())
                    cleaned_last = " ".join(last_text.split()) if last_text else ""
                    self.after(0, self._append_mic_text, cleaned_text, cleaned_last)
                    last_text = text

            time.sleep(0.02)

    def _append_mic_text(self, new_text: str, previous_segment: str):
        current_content = self.textbox.get("1.0", "end-1c").rstrip()

        if previous_segment and current_content.endswith(previous_segment):
            base_content = current_content[:-len(previous_segment)].rstrip()
            prefix = " " if base_content else ""
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", base_content + prefix + new_text)
        else:
            prefix = " " if current_content else ""
            self.textbox.insert("end", prefix + new_text)

        self.textbox.see("end")

    # --- File Import & Cancellation Logic ---
    def open_file_dialog(self):
        filetypes = [
            ("All Supported Files", "*.docx *.pdf *.png *.jpg *.jpeg *.bmp *.wav *.mp3 *.mp4 *.mov"),
            ("Documents", "*.docx *.pdf"),
            ("Images (OCR)", "*.png *.jpg *.jpeg *.bmp"),
            ("Audio Files", "*.wav *.mp3"),
            ("Video Files", "*.mp4 *.mov"),
        ]

        file_path = filedialog.askopenfilename(title="Select File for Processing", filetypes=filetypes)
        if not file_path:
            return

        self.cancel_event.clear()

        # Swap Import File button for Cancel button
        self.file_btn.pack_forget()
        self.cancel_btn.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.toggle_btn.configure(state="disabled")

        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Processing File (0%)...", text_color="orange")

        threading.Thread(target=self._file_worker, args=(file_path,), daemon=True).start()

    def cancel_file_processing(self):
        self.cancel_event.set()
        self.status_label.configure(text="Status: Cancelling...", text_color="red")

    def _update_progress(self, ratio: float):
        if self.cancel_event.is_set():
            return
        percent = int(ratio * 100)
        self.after(0, lambda p=ratio: self.progress_bar.set(p))
        self.after(
            0,
            lambda pct=percent: self.status_label.configure(
                text=f"Status: Processing File ({pct}%)...", text_color="orange"
            ),
        )

    def _file_worker(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        try:
            is_cancelled = self.cancel_event.is_set

            if ext in self.doc_processor.supported_extensions:
                result = self.doc_processor.process(
                    file_path, progress_callback=self._update_progress, is_cancelled=is_cancelled
                )
            elif ext in self.img_processor.supported_extensions:
                result = self.img_processor.process(
                    file_path, progress_callback=self._update_progress, is_cancelled=is_cancelled
                )
            elif ext in self.audio_processor.supported_extensions:
                result = self.audio_processor.process(
                    file_path, progress_callback=self._update_progress, is_cancelled=is_cancelled
                )
            elif ext in self.video_processor.supported_extensions:
                result = self.video_processor.process(
                    file_path, progress_callback=self._update_progress, is_cancelled=is_cancelled
                )
            else:
                raise ValueError(f"Unsupported file format: {ext}")

            if self.cancel_event.is_set():
                self.after(0, self._on_file_cancelled)
            else:
                self.after(0, self._on_file_complete, result)

        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_file_error(msg))

    def _reset_control_buttons(self):
        self.cancel_btn.pack_forget()
        self.file_btn.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.toggle_btn.configure(state="normal")
        self.file_btn.configure(state="normal")

    def _on_file_complete(self, result: str):
        self.progress_bar.set(1.0)

        if result and result.strip():
            single_paragraph = " ".join(result.split())
            current_content = self.textbox.get("1.0", "end-1c").rstrip()

            prefix = " " if current_content else ""
            self.textbox.insert("end", prefix + single_paragraph)
            self.textbox.see("end")

        self.status_label.configure(text="Status: Ready", text_color="green")
        self._reset_control_buttons()

        self.after(1500, lambda: self.progress_bar.set(0))

    def _on_file_cancelled(self):
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Process Cancelled", text_color="orange")
        self._reset_control_buttons()

        self.after(2000, lambda: self.status_label.configure(text="Status: Ready", text_color="green"))

    def _on_file_error(self, err_msg: str):
        self.progress_bar.set(0)
        self.textbox.insert("end", f"\n[Error processing file: {err_msg}]\n")
        self.status_label.configure(text="Status: Error", text_color="red")
        self._reset_control_buttons()

    def clear_text(self):
        self.textbox.delete("1.0", "end")


if __name__ == "__main__":
    app = CaecusApp()
    app.mainloop()