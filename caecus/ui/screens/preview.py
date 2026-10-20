from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageOps

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.tasks import Task
from caecus.ui.player import AudioPlayer, compute_peaks, decode_overview, fmt_time
from caecus.ui.widgets import Card, Waveform, primary_button, secondary_button

MAX_TEXT_CHARS = 3000
HEADINGS = {
    "image": ("Preview image", "Check your attachment before converting."),
    "document": ("Preview document", "Read the page before converting."),
    "audio": ("Preview audio", "Listen before converting speech to text."),
    "video": ("Preview video", "Check the video before converting speech to text."),
}
READY = {"image": "Image ready", "document": "Document ready",
         "audio": "Audio ready", "video": "Video ready"}


def human_size(num):
    if num < 1024:
        return f"{num} B"
    if num < 1024 ** 2:
        return f"{num / 1024:.0f} KB"
    return f"{num / 1024 ** 2:.1f} MB"


class PreviewScreen(Screen):
    name = "preview"
    step = 2
    heading = "Preview"
    subheading = "Check your attachment before converting."

    def build(self):
        self._pdf = None
        self._task = None
        self._player, self._poll_id, self._dragging, self._was_playing = None, None, False, False
        ws = self.workspace
        ws.grid_columnconfigure(0, weight=1)
        ws.grid_rowconfigure(0, weight=1)
        card = Card(ws)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 8))
        head.grid_columnconfigure(0, weight=1)
        self.file_label = ctk.CTkLabel(head, text="", font=T.font(15, "bold"),
                                       text_color=T.TEXT, anchor="w")
        self.file_label.grid(row=0, column=0, sticky="w")
        self.meta_label = ctk.CTkLabel(head, text="", font=T.font(12), text_color=T.MUTED, anchor="e")
        self.meta_label.grid(row=0, column=1, sticky="e")
        ctk.CTkFrame(card, fg_color=T.BORDER, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew")
        self.body = ctk.CTkFrame(card, fg_color=T.BG, corner_radius=0)
        self.body.grid(row=2, column=0, sticky="nsew", padx=1, pady=(0, 1))

        self.actions.grid_columnconfigure(1, weight=1)
        self.change_btn = secondary_button(self.actions, "< Change file", self._change, width=150)
        self.change_btn.grid(row=0, column=0, sticky="w")
        self.convert_btn = primary_button(self.actions, "Convert to text", self._convert, width=180)
        self.convert_btn.grid(row=0, column=2, sticky="e")

    # ---- lifecycle -----------------------------------------------------
    def on_show(self, path=None, kind=None, **ctx):
        self._close_pdf()
        self._close_media()
        self._task = None
        self.path, self.kind = Path(path), kind
        self.heading, self.subheading = HEADINGS.get(kind, HEADINGS["image"])
        self.file_label.configure(text=self.path.name)
        self._reset_buttons()
        for child in self.body.winfo_children():
            child.destroy()
        self.update_idletasks()
        size = human_size(self.path.stat().st_size)
        try:
            if kind == "image":
                self._render_image(size)
            elif kind == "audio":
                self._render_audio(size)
            elif kind == "video":
                self._render_video(size)
            elif self.path.suffix.lower() == ".pdf":
                self._render_pdf(size)
            else:
                self._render_text(size)
        except Exception as exc:
            self.meta_label.configure(text="")
            ctk.CTkLabel(self.body, text=f"Cannot preview this file ({exc})", font=T.font(13),
                         text_color=T.MUTED, wraplength=int(500 * T.SCALE)).place(relx=0.5, rely=0.5, anchor="center")
        self.app.status.set(f"{READY.get(kind, 'File ready')}  |  Change file returns to Import / attach")

    def on_hide(self):
        self._close_pdf()
        self._close_media()

    def _close_pdf(self):
        if self._pdf is not None:
            try:
                self._pdf.close()
            except Exception:
                pass
        self._pdf = None

    # ---- renderers -----------------------------------------------------
    def _fit_image(self, img, holder):
        self.update_idletasks()
        box_w = max(120, holder.winfo_width() - int(24 * T.SCALE))
        box_h = max(80, holder.winfo_height() - int(24 * T.SCALE))
        shown = img.copy()
        if shown.mode not in ("RGB", "RGBA"):
            shown = shown.convert("RGBA")
        shown.thumbnail((box_w, box_h), Image.Resampling.BILINEAR)
        logical = (max(1, round(shown.width / T.SCALE)), max(1, round(shown.height / T.SCALE)))
        photo = ctk.CTkImage(light_image=shown, dark_image=shown, size=logical)
        label = ctk.CTkLabel(holder, image=photo, text="")
        label.image = photo
        label.place(relx=0.5, rely=0.5, anchor="center")
        self.app.repaint_soon()

    def _render_image(self, size):
        src = Image.open(self.path)
        fmt = (src.format or self.path.suffix.lstrip(".")).upper()
        img = ImageOps.exif_transpose(src)
        self.meta_label.configure(text=f"{fmt} image  |  {img.width} x {img.height}  |  {size}")
        self._fit_image(img, self.body)

    def _render_pdf(self, size):
        import pymupdf
        self._pdf = pymupdf.open(self.path)
        self._page, self._pages = 0, len(self._pdf)
        plural = "s" if self._pages != 1 else ""
        self.meta_label.configure(text=f"PDF document  |  {self._pages} page{plural}  |  {size}")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=0)
        self.body.grid_rowconfigure(0, weight=1)
        self.page_holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.page_holder.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        nav = ctk.CTkFrame(self.body, fg_color="transparent")
        nav.grid(row=0, column=1, sticky="ns", padx=(0, 24))
        nav.grid_rowconfigure((0, 2), weight=1)
        inner = ctk.CTkFrame(nav, fg_color="transparent")
        inner.grid(row=1, column=0)
        self.page_label = ctk.CTkLabel(inner, text="", font=T.font(14, "bold"), text_color=T.TEXT)
        self.page_label.pack(pady=(0, 8))
        arrows = ctk.CTkFrame(inner, fg_color="transparent")
        arrows.pack()
        self.prev_btn = secondary_button(arrows, "<", lambda: self._turn(-1), width=48)
        self.prev_btn.pack(side="left", padx=4)
        self.next_btn = secondary_button(arrows, ">", lambda: self._turn(1), width=48)
        self.next_btn.pack(side="left", padx=4)
        ctk.CTkLabel(inner, text="Fit page", font=T.font(12), text_color=T.MUTED).pack(pady=(8, 0))
        self._show_page()

    def _turn(self, delta):
        self._page = min(max(self._page + delta, 0), self._pages - 1)
        self._show_page()

    def _show_page(self):
        for child in self.page_holder.winfo_children():
            child.destroy()
        pix = self._pdf[self._page].get_pixmap(dpi=100)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self._fit_image(img, self.page_holder)
        self.page_label.configure(text=f"Page {self._page + 1} of {self._pages}")
        self.prev_btn.configure(state="normal" if self._page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self._page < self._pages - 1 else "disabled")

    def _render_text(self, size):
        if self.path.suffix.lower() == ".docx":
            import docx
            text = "\n\n".join(p.text for p in docx.Document(self.path).paragraphs if p.text.strip())
            label = "Word document"
        else:
            text = self.path.read_text(encoding="utf-8", errors="ignore")
            label = "Text file"
        shown = text[:MAX_TEXT_CHARS]
        self.meta_label.configure(text=f"{label}  |  {len(text)} characters  |  {size}")
        paper = ctk.CTkFrame(self.body, fg_color=T.CARD, corner_radius=4, border_width=1, border_color=T.BORDER)
        paper.pack(fill="both", expand=True, padx=14, pady=14)
        box = ctk.CTkTextbox(paper, wrap="word", fg_color=T.CARD, text_color=T.TEXT, font=T.font(14))
        box.pack(fill="both", expand=True, padx=8, pady=8)
        box.insert("1.0", shown or "[ This file contains no text ]")
        if len(text) > len(shown):
            box.insert("end", f"\n\n[ Showing the first {len(shown)} of {len(text)} characters. "
                              f"The full file is converted. ]")
        box.configure(state="disabled")

    # ---- actions -------------------------------------------------------
    # ---- audio / video -------------------------------------------------
    def _close_media(self):
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        if self._player is not None:
            try:
                self._player.close()
            except Exception:
                pass
        self._player = None

    def _render_audio(self, size):
        ext = self.path.suffix.lstrip(".").upper()
        try:
            samples, rate = decode_overview(self.path)
            peaks = compute_peaks(samples)
            self._player = AudioPlayer(self.path, len(samples) / rate)
        except Exception as exc:
            self.meta_label.configure(text=f"{ext} audio  |  {size}")
            ctk.CTkLabel(self.body, text=f"Playback preview unavailable ({exc}).\nYou can still convert this file.",
                         font=T.font(13), text_color=T.MUTED,
                         wraplength=int(500 * T.SCALE)).place(relx=0.5, rely=0.5, anchor="center")
            return
        duration = self._player.duration
        self.meta_label.configure(text=f"{ext} audio  |  {fmt_time(duration)}  |  {size}")
        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 4))
        ctk.CTkLabel(top, text=self.path.stem, font=T.font(16, "bold"), text_color=T.TEXT,
                     anchor="w").pack(side="left")
        self.audio_state = ctk.CTkLabel(top, text="Paused", font=T.font(12), text_color=T.MUTED)
        self.audio_state.pack(side="left", padx=10)
        self.wave = Waveform(self.body, peaks)
        self.wave.pack(pady=8)
        controls = ctk.CTkFrame(self.body, fg_color=T.CARD, corner_radius=6)
        controls.pack(fill="x", padx=18, pady=(4, 6))
        controls.grid_columnconfigure(2, weight=1)
        self.play_btn = secondary_button(controls, "Play", self._toggle_play, width=100)
        self.play_btn.grid(row=0, column=0, padx=(10, 10), pady=8)
        self.elapsed = ctk.CTkLabel(controls, text="00:00", font=T.font(12), text_color=T.MUTED)
        self.elapsed.grid(row=0, column=1)
        self.slider = ctk.CTkSlider(controls, from_=0, to=max(duration, 0.1), fg_color=T.MARKER_OFF,
                                    progress_color=T.PRIMARY, button_color=T.PRIMARY,
                                    button_hover_color=T.PRIMARY_HOVER)
        self.slider.set(0)
        self.slider.grid(row=0, column=2, sticky="ew", padx=10)
        self.slider.bind("<ButtonPress-1>", lambda _e: setattr(self, "_dragging", True), add="+")
        self.slider.bind("<ButtonRelease-1>", self._on_slide_release, add="+")
        ctk.CTkLabel(controls, text=fmt_time(duration), font=T.font(12), text_color=T.MUTED).grid(
            row=0, column=3, padx=(0, 12))
        ctk.CTkLabel(self.body, text="Play to check the recording, then convert when you're ready.",
                     font=T.font(12), text_color=T.MUTED).pack(pady=(2, 0))
        self._was_playing = False
        self._poll_id = self.after(100, self._poll_audio)
        self.app.repaint_soon()

    def _toggle_play(self):
        if self._player is None:
            return
        try:
            if self._player.playing:
                self._player.pause()
                self._set_play_ui(False)
            else:
                self._player.play()
                self._set_play_ui(True)
        except Exception as exc:
            self._set_play_ui(False)
            self.app.status.set(f"Cannot play audio: {exc}"[:150], "error")

    def _set_play_ui(self, playing):
        self._was_playing = playing
        self.play_btn.configure(text="Pause" if playing else "Play")
        self.audio_state.configure(text="Playing" if playing else "Paused")

    def _on_slide_release(self, _event):
        self._dragging = False
        if self._player is not None:
            try:
                self._player.seek(self.slider.get())
            except Exception as exc:
                self.app.status.set(f"Cannot seek: {exc}"[:150], "error")

    def _poll_audio(self):
        player = self._player
        if player is None:
            return
        pos = player.position()
        if not self._dragging:
            self.slider.set(min(pos, player.duration))
        self.wave.set_progress(pos / player.duration if player.duration else 0.0)
        self.elapsed.configure(text=fmt_time(pos))
        if self._was_playing and not player.playing:  # reached the end, or ffplay failed
            player.pause()
            self._set_play_ui(False)
            if player.failed:
                player.failed = False
                self.app.status.set("Could not play audio: ffplay stopped right away "
                                    "(check the Pi's audio output)", "error")
        self._poll_id = self.after(100, self._poll_audio)

    def _render_video(self, size):
        import cv2
        cap = cv2.VideoCapture(str(self.path))
        if not cap.isOpened():
            raise RuntimeError("the video could not be opened")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ok, frame = cap.read()
        cap.release()
        ext = self.path.suffix.lstrip(".").upper()
        duration = fmt_time(frames / fps) if fps else "--:--"
        self.meta_label.configure(text=f"{ext} video  |  {duration}  |  {width} x {height}  |  {size}")
        if ok:
            self._fit_image(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), self.body)
        ctk.CTkLabel(self.body, text="Playback preview comes in the next slice", font=T.font(12),
                     text_color=T.MUTED).place(relx=0.5, rely=0.96, anchor="s")

    def _reset_buttons(self):
        self.change_btn.configure(state="normal")
        self.convert_btn.configure(text="Convert to text", command=self._convert,
                                   fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOVER)

    def _change(self):
        if self._task is None:
            self.app.show("attach")

    def _convert(self):
        if self.kind in ("audio", "video"):
            t = self.app.transcriber
            if t.asr_state != "ready":
                if t.asr_state == "error":
                    self.app.status.set(f"Speech engine failed to load: {t.asr_error}"[:150], "error")
                else:
                    self.app.status.set("Speech engine is still loading, try again in a moment", "warn")
                return
            if self._player is not None and self._player.playing:
                self._player.pause()
                self._set_play_ui(False)
        self.change_btn.configure(state="disabled")
        self.convert_btn.configure(text="Cancel", command=self._cancel,
                                   fg_color=T.DANGER, hover_color="#8F2B2B")
        self.app.status.set("Converting...  0%", "warn")
        self._task = Task(self.app, self._work, on_progress=self._progress, on_done=self._done,
                          on_error=self._failed, on_cancel=self._cancelled)
        self._task.start()

    def _work(self, progress, is_cancelled):
        return self.app.transcriber.convert(self.kind, str(self.path), progress, is_cancelled)

    def _cancel(self):
        if self._task:
            self._task.cancel()
            self.app.status.set("Cancelling...", "warn")

    def _progress(self, ratio):
        self.app.status.set(f"Converting...  {int(ratio * 100)}%", "warn")

    def _done(self, text):
        self._task = None
        self._reset_buttons()
        if text and text.strip():
            self.app.show("edit", text=text, source=self.path.name)
        else:
            self.app.status.set("No speech found in this file" if self.kind in ("audio", "video")
                                else "No text found in this file", "warn")

    def _failed(self, exc):
        self._task = None
        self._reset_buttons()
        self.app.status.set(f"Could not convert: {exc}"[:150], "error")

    def _cancelled(self):
        self._task = None
        self._reset_buttons()
        self.app.status.set("Conversion cancelled", "warn")
