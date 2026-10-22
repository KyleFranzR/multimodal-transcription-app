from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.widgets import Card, make_tappable, primary_button, secondary_button

from caecus.ui.player import fmt_time

PLACEHOLDER = "Type or paste text here..."
DEFAULT_MIC = "System default"

MAX_RECORD_SECONDS = 120  # auto stopper recording

def _types(label, exts):
    patterns = " ".join(f"*{e} *{e.upper()}" for e in exts)
    return [(label, patterns)]


CATEGORIES = (
    ("image", "Images", ".bmp, .jpeg, .png", _types("Images", (".bmp", ".jpeg", ".jpg", ".png"))),
    ("document", "Documents", ".txt, .docx, .pdf", _types("Documents", (".txt", ".docx", ".pdf"))),
    ("audio", "Audio", ".mp3, .ogg", _types("Audio", (".mp3", ".ogg"))),
    ("video", "Video", ".mp4, .mov", _types("Video", (".mp4", ".mov"))),
)


class AttachScreen(Screen):
    name = "attach"
    heading = "Import / attach"
    subheading = "Choose one file, speak, or enter text."
    step = 1

    def build(self):
        ws = self.workspace
        ws.grid_columnconfigure(0, weight=488, uniform="main")
        ws.grid_columnconfigure(1, weight=268, uniform="main")
        ws.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(ws, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_columnconfigure((0, 1), weight=1, uniform="cat")
        left.grid_rowconfigure((0, 1), weight=1, uniform="cat")
        for idx, (kind, label, formats, types) in enumerate(CATEGORIES):
            self._category_card(left, idx, kind, label, formats, types)

        right = ctk.CTkFrame(ws, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=106, uniform="right")
        right.grid_rowconfigure(1, weight=158, uniform="right")
        self._speech_card(right)
        self._text_card(right)

        self.actions.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.actions, text="Select a category to browse for a file.",
                     font=T.font(13), text_color=T.MUTED).grid(row=0, column=0, sticky="w", pady=10)
        ctk.CTkLabel(self.actions, text="Physical keyboard supported",
                     font=T.font(13), text_color=T.MUTED).grid(row=0, column=2, sticky="e", pady=10)

    # ---- widgets -------------------------------------------------------
    def _category_card(self, parent, idx, kind, label, formats, types):
        col, row = idx % 2, idx // 2
        card = Card(parent)
        card.grid(row=row, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0), pady=(0, 6) if row == 0 else (6, 0))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))
        browse = ctk.CTkLabel(top, text="Browse >", font=T.font(12), text_color=T.PRIMARY)
        browse.pack(side="right")
        name = ctk.CTkLabel(card, text=label, font=T.font(18, "bold"), text_color=T.TEXT, anchor="w")
        name.pack(fill="x", padx=14, pady=(14, 0))
        fmt = ctk.CTkLabel(card, text=formats, font=T.font(13), text_color=T.MUTED, anchor="w")
        fmt.pack(fill="x", padx=14, pady=(6, 0))
        make_tappable(lambda k=kind, t=types: self._browse(k, t), card, top, browse, name, fmt)

    def _speech_card(self, parent):
        card = Card(parent)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        card.pack_propagate(False)  # huwag baguhin ang laki ng card ayon sa laman
        self._recorder, self._rec_after = None, None

        # idle: ang dating itsura
        self._idle = ctk.CTkFrame(card, fg_color="transparent")
        mic_row = ctk.CTkFrame(self._idle, fg_color="transparent")
        mic_row.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(mic_row, text="Transcribe speech", font=T.font(13), text_color=T.MUTED,
                     anchor="w").pack(side="left")
        self._mic_menu = ctk.CTkOptionMenu(
            mic_row, values=[DEFAULT_MIC], width=170, height=26, font=T.font(11),
            dropdown_font=T.font(12), fg_color=T.BG, button_color=T.BORDER,
            button_hover_color=T.PRIMARY_TINT, text_color=T.TEXT, command=self._on_mic)
        self._mic_menu.pack(side="right")
        primary_button(self._idle, "Speak", self._speak).pack(fill="x", padx=12, pady=(0, 12))

        # recording: timer + Stop
        self._rec = ctk.CTkFrame(card, fg_color="transparent")
        top = ctk.CTkFrame(self._rec, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(top, text="Recording...", font=T.font(13), text_color=T.DANGER,
                     anchor="w").pack(side="left")
        self._rec_timer = ctk.CTkLabel(top, text="00:00", font=T.font(16, "bold"), text_color=T.TEXT)
        self._rec_timer.pack(side="right")
        ctk.CTkButton(self._rec, text="Stop", command=self._stop_recording, height=44, corner_radius=8,
                      fg_color=T.DANGER, hover_color="#8F2B2B", text_color="#FFFFFF",
                      font=T.font(15, "bold")).pack(fill="x", padx=12, pady=(0, 12))

        self._idle.pack(fill="both", expand=True)

    def _text_card(self, parent):
        card = Card(parent)
        card.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        ctk.CTkLabel(card, text="Type text", font=T.font(14, "bold"), text_color=T.TEXT,
                     anchor="w").pack(fill="x", padx=12, pady=(12, 6))
        self.entry = ctk.CTkTextbox(card, height=48, wrap="word", fg_color=T.BG, border_width=1,
                                    border_color=T.BORDER, text_color=T.MUTED, font=T.font(13))
        self.entry.pack(fill="x", padx=12)
        self._placeholder_on = True
        self.entry.insert("1.0", PLACEHOLDER)
        self.entry.bind("<FocusIn>", self._entry_focus_in, add="+")
        self.entry.bind("<FocusOut>", self._entry_focus_out, add="+")
        secondary_button(card, "Use typed text", self._use_typed).pack(fill="x", padx=12, pady=(8, 12))

    # ---- placeholder handling -----------------------------------------
    def _entry_focus_in(self, _event=None):
        if self._placeholder_on:
            self.entry.delete("1.0", "end")
            self.entry.configure(text_color=T.TEXT)
            self._placeholder_on = False

    def _entry_focus_out(self, _event=None):
        if not self.entry.get("1.0", "end-1c").strip():
            self.entry.delete("1.0", "end")
            self.entry.insert("1.0", PLACEHOLDER)
            self.entry.configure(text_color=T.MUTED)
            self._placeholder_on = True

    def _typed_text(self):
        return "" if self._placeholder_on else self.entry.get("1.0", "end-1c")

    # ---- actions (navigation is wired up in later slices) --------------
    def on_show(self, **ctx):
        self.entry.delete("1.0", "end")
        self._placeholder_on = False
        self._entry_focus_out()
        self._load_mics()
        self.refresh_status()

    def refresh_status(self):
        t = self.app.transcriber
        if t.asr_state == "error":
            self.app.status.set(f"Speech engine failed to load: {t.asr_error}"[:150], "error")
        elif t.asr_state == "ready":
            self.app.status.set("Ready for import  |  Speech engine ready", "ok")
        else:
            self.app.status.set("Loading speech engine...  |  Documents, images and typed text are ready", "warn")

    def _browse(self, kind, types):
        path = filedialog.askopenfilename(
            parent=self.app, title=f"Select a {kind} file", initialdir=self.app.last_dir, filetypes=types)
        if not path:
            return
        self.app.last_dir = str(Path(path).parent)
        self.app.show("preview", path=path, kind=kind)

    def _speak(self):
        if self._recorder is not None:
            return
        try:
            from caecus.ui.recorder import Recorder
            rec = Recorder()
            rec.start()
        except Exception as exc:
            self.app.status.set(f"Cannot start recording: {exc}"[:150], "error")
            return
        self._recorder = rec
        self._rec_timer.configure(text="00:00")
        self._idle.pack_forget()
        self._rec.pack(fill="both", expand=True)
        self.app.status.set("Recording...  Press Stop when you are done", "warn")
        self.app.repaint_soon()
        self._tick()

    def _tick(self):
        rec = self._recorder
        if rec is None:
            return
        secs = rec.elapsed()
        self._rec_timer.configure(text=fmt_time(secs))
        if secs >= MAX_RECORD_SECONDS:
            self._stop_recording()
            return
        self._rec_after = self.after(100, self._tick)

    def _cancel_timer(self):
        if self._rec_after is not None:
            try:
                self.after_cancel(self._rec_after)
            except Exception:
                pass
            self._rec_after = None

    def _show_idle(self):
        self._rec.pack_forget()
        self._idle.pack(fill="both", expand=True)
        self.app.repaint_soon()

    def _stop_recording(self):
        rec, self._recorder = self._recorder, None
        self._cancel_timer()
        self._show_idle()
        if rec is None:
            return
        try:
            path = rec.stop()
        except Exception as exc:
            self.app.status.set(f"Could not save the recording: {exc}"[:150], "error")
            return
        if path is None or rec.elapsed() < 0.5:
            self.app.status.set("Recording was too short, please try again", "warn")
            return
        self.app.show("preview", path=str(path), kind="audio")

    def on_hide(self):
        # umalis sa screen habang nagre-record: itapon ang recording
        self._cancel_timer()
        rec, self._recorder = self._recorder, None
        if rec is not None:
            try:
                rec.cancel()
            except Exception:
                pass
        self._show_idle()

    def _use_typed(self):
        text = self._typed_text()
        if not text.strip():
            self.app.status.set("Type or paste some text first", "warn")
            return
        self.app.show("edit", text=text, source="Typed text")

    def _load_mics(self):
        try:
            from caecus.ui import recorder
            names = [DEFAULT_MIC] + recorder.input_devices()
            saved = recorder.load_choice()
        except Exception:
            return  # walang sounddevice: ipapakita ng Speak ang error
        self._mic_menu.configure(values=names)
        self._mic_menu.set(saved if saved in names else DEFAULT_MIC)

    def _on_mic(self, choice):
        try:
            from caecus.ui import recorder
            recorder.save_choice("" if choice == DEFAULT_MIC else choice)
        except Exception:
            pass