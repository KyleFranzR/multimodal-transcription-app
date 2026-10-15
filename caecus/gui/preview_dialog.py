from pathlib import Path
import subprocess
import time
import tkinter as tk
import customtkinter as ctk
import docx
import pymupdf
from PIL import Image, ImageTk

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from ffpyplayer.player import MediaPlayer
    HAS_FFPY = True
except ImportError:
    HAS_FFPY = False

# Hard Preview Limits
MAX_PDF_PAGES = 5
MAX_DOCX_PARAGRAPHS = 10
MAX_DOCX_CHARS = 1500
MAX_MEDIA_DURATION_SEC = 30


class PreviewDialog(ctk.CTkFrame):
    def __init__(self, parent, on_confirm_callback, on_close_callback=None, **kwargs):
        # Enforce fixed 460px width
        kwargs["width"] = kwargs.get("width", 460)
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=0, **kwargs)
        
        # Prevent children widgets from altering panel width
        self.pack_propagate(False)
        self.grid_propagate(False)

        self.on_confirm_callback = on_confirm_callback
        self.on_close_callback = on_close_callback

        self.file_path = None
        self.is_playing = False
        self.playback_start_time = 0.0
        self.audio_process = None
        self.audio_player = None
        self.video_cap = None
        self.current_tk_img = None
        self.canvas_image_id = None
        self.timer_id = None

        self._setup_ui()

    def show_file(self, file_path: str):
        """Loads and renders a new file inside the fixed-size panel."""
        self._stop_media()
        self.file_path = Path(file_path).resolve()

        # Clear previous visual content
        for child in self.canvas_frame.winfo_children():
            child.destroy()

        self.header_label.configure(text=f"Preview - {self.file_path.name}")
        self._render_visual_preview()

    def _setup_ui(self):
        # Header Bar
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(padx=15, pady=(15, 5), fill="x", side="top")

        self.header_label = ctk.CTkLabel(
            header_frame,
            text="Document Preview",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        )
        self.header_label.pack(side="left", fill="x", expand=True)

        close_btn = ctk.CTkButton(
            header_frame,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=self._hide_panel
        )
        close_btn.pack(side="right")

        # Action Buttons Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=15, pady=15, fill="x", side="bottom")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="#3a3a3a",
            hover_color="#505050",
            command=self._hide_panel,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=(0, 5), expand=True, fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Confirm and Transcribe",
            fg_color="#007ACC",
            hover_color="#005999",
            command=self._confirm,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="right", padx=(5, 0), expand=True, fill="x")

        # Scrollable Viewport
        self.canvas_frame = ctk.CTkScrollableFrame(self, fg_color="#141414", corner_radius=6)
        self.canvas_frame.pack(padx=15, pady=5, fill="both", expand=True, side="top")

    def _render_visual_preview(self):
        if not self.file_path or not self.file_path.exists():
            return

        ext = self.file_path.suffix.lower()

        if ext in {".png", ".jpg", ".jpeg", ".bmp"}:
            img = Image.open(self.file_path)
            self._add_image_page(img)
            ctk.CTkLabel(
                self.canvas_frame,
                text=f"Resolution: {img.width} x {img.height} px",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).pack(pady=(2, 10))

        elif ext == ".pdf":
            with pymupdf.open(self.file_path) as doc:
                total_pages = len(doc)
                pages_to_show = min(total_pages, MAX_PDF_PAGES)

                for idx in range(pages_to_show):
                    pix = doc[idx].get_pixmap(dpi=120)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ctk.CTkLabel(
                        self.canvas_frame,
                        text=f"Page {idx + 1} of {total_pages}",
                        font=ctk.CTkFont(size=12),
                        text_color="gray"
                    ).pack(pady=(10, 2))
                    self._add_image_page(img)

                if total_pages > MAX_PDF_PAGES:
                    ctk.CTkLabel(
                        self.canvas_frame,
                        text=f"Displaying first {MAX_PDF_PAGES} of {total_pages} pages. Full file will be transcribed.",
                        font=ctk.CTkFont(size=12, weight="bold"),
                        text_color="#007ACC",
                        wraplength=380
                    ).pack(pady=(10, 15))

        elif ext == ".docx":
            doc = docx.Document(self.file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()][:MAX_DOCX_PARAGRAPHS]
            text = "\n\n".join(paragraphs)[:MAX_DOCX_CHARS]

            paper = ctk.CTkFrame(self.canvas_frame, fg_color="#FFFFFF", corner_radius=4)
            paper.pack(padx=10, pady=10, fill="both", expand=True)

            tb = ctk.CTkTextbox(
                paper,
                font=ctk.CTkFont(family="Times New Roman", size=13),
                text_color="#111111",
                fg_color="#FFFFFF",
                wrap="word",
                height=320
            )
            tb.pack(padx=10, pady=10, fill="both", expand=True)
            tb.insert("1.0", text or "[ Document contains no extractable text ]")
            tb.configure(state="disabled")

        elif ext in {".wav", ".mp3", ".mp4", ".mov"}:
            self._render_media_card(ext)

    def _add_image_page(self, pil_image: Image.Image):
        pil_image.thumbnail((380, 520), Image.Resampling.BILINEAR)
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
        ctk.CTkLabel(self.canvas_frame, image=ctk_img, text="").pack(pady=10, expand=True)

    def _render_media_card(self, ext: str):
        card = ctk.CTkFrame(self.canvas_frame, fg_color="#252525", corner_radius=8)
        card.pack(padx=10, pady=10, fill="both", expand=True)

        self.is_audio = ext in {".wav", ".mp3"}
        self.canvas = tk.Canvas(card, height=260, bg="#121212", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10, fill="both", expand=True)

        self.media_display = ctk.CTkLabel(
            card,
            text=f"{self.file_path.name}\n\nPlayback Active - 0:30 remaining",
            font=ctk.CTkFont(size=14)
        )
        self.media_display.pack(pady=(0, 10))

        self.play_btn = ctk.CTkButton(
            card,
            text="Play Media Snippet",
            command=self._toggle_media_playback,
            fg_color="#007ACC",
            hover_color="#005999",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.play_btn.pack(pady=(0, 15), padx=15, fill="x")

    def _toggle_media_playback(self):
        if self.is_playing:
            self._stop_media()
        else:
            self._start_media()

    def _start_media(self):
        self.is_playing = True
        self.playback_start_time = time.time()
        self.play_btn.configure(text="Stop Playback", fg_color="#8B0000", hover_color="#660000")

        if self.is_audio:
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(self.file_path)]
            try:
                self.audio_process = subprocess.Popen(cmd)
            except FileNotFoundError:
                if self.file_path.suffix.lower() == ".wav":
                    self.audio_process = subprocess.Popen(["aplay", "-q", str(self.file_path)])
                else:
                    self.media_display.configure(text="Error: Audio player binary (ffplay) not found.")
                    self._stop_media()
                    return
        else:
            if HAS_FFPY:
                try:
                    self.audio_player = MediaPlayer(str(self.file_path), ff_opts={'autoexit': True})
                except Exception:
                    self.audio_player = None

            if HAS_OPENCV:
                self.video_cap = cv2.VideoCapture(str(self.file_path))

        self.canvas_image_id = None
        self._update_media_loop()

    def _update_media_loop(self):
        if not self.is_playing:
            return

        elapsed = time.time() - self.playback_start_time

        if elapsed >= MAX_MEDIA_DURATION_SEC:
            self._stop_media(reached_limit=True)
            return

        if self.is_audio:
            if self.audio_process is None or self.audio_process.poll() is not None:
                self._stop_media()
                return

            sec_left = int(MAX_MEDIA_DURATION_SEC - elapsed)
            self.media_display.configure(text=f"{self.file_path.name}\n\nPlayback Active - 0:{sec_left:02d} remaining")
            self.timer_id = self.after(100, self._update_media_loop)
            return

        if self.audio_player:
            _, val = self.audio_player.get_frame()
            if val == 'eof':
                self._stop_media()
                return

        if self.video_cap and self.video_cap.isOpened():
            ret, frame = self.video_cap.read()
            if ret:
                c_w = self.canvas.winfo_width() or 380
                c_h = self.canvas.winfo_height() or 260
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((c_w, c_h), Image.Resampling.BILINEAR)
                self.current_tk_img = ImageTk.PhotoImage(img)

                if self.canvas_image_id is None:
                    self.canvas_image_id = self.canvas.create_image(c_w // 2, c_h // 2, image=self.current_tk_img, anchor="center")
                else:
                    self.canvas.itemconfig(self.canvas_image_id, image=self.current_tk_img)
            else:
                self._stop_media()
                return

        sec_left = int(MAX_MEDIA_DURATION_SEC - elapsed)
        self.media_display.configure(text=f"{self.file_path.name}\n\nPlayback Active - 0:{sec_left:02d} remaining")
        self.timer_id = self.after(30, self._update_media_loop)

    def _cleanup_handles(self):
        self.is_playing = False

        if self.timer_id is not None:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        if self.audio_process is not None:
            try:
                self.audio_process.terminate()
                self.audio_process.wait(timeout=0.2)
            except Exception:
                try:
                    self.audio_process.kill()
                except Exception:
                    pass
            self.audio_process = None

        if self.video_cap is not None:
            if self.video_cap.isOpened():
                self.video_cap.release()
            self.video_cap = None

        if self.audio_player is not None:
            try:
                self.audio_player.set_pause(True)
                self.audio_player.close_player()
            except Exception:
                pass
            self.audio_player = None

    def _stop_media(self, reached_limit: bool = False):
        self._cleanup_handles()

        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.delete("all")
            self.canvas_image_id = None

        if hasattr(self, "play_btn") and self.play_btn.winfo_exists():
            self.play_btn.configure(text="Play Media Snippet", fg_color="#007ACC", hover_color="#005999")

        if hasattr(self, "media_display") and self.media_display.winfo_exists():
            if reached_limit:
                self.media_display.configure(
                    text=f"{self.file_path.name}\n\nPlayback Limit Reached (30s max)"
                )
            elif self.file_path:
                self.media_display.configure(
                    text=f"{self.file_path.name}\n\nPlayback Active - 0:30 remaining"
                )

    def _hide_panel(self):
        self._stop_media()
        self.pack_forget()
        if self.on_close_callback:
            self.on_close_callback()

    def _confirm(self):
        self._stop_media()
        if self.file_path and self.on_confirm_callback:
            self.on_confirm_callback(str(self.file_path))