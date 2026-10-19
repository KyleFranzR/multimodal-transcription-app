from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.widgets import Card, make_tappable, primary_button, secondary_button

PLACEHOLDER = "Type or paste text here..."


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
        ws.grid_columnconfigure(0, weight=488)
        ws.grid_columnconfigure(1, weight=268)
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
        right.grid_rowconfigure(0, weight=106)
        right.grid_rowconfigure(1, weight=158)
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
        ctk.CTkLabel(card, text="Transcribe speech", font=T.font(13), text_color=T.MUTED,
                     anchor="w").pack(fill="x", padx=12, pady=(12, 6))
        primary_button(card, "Speak", self._speak).pack(fill="x", padx=12, pady=(0, 12))

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
        self.app.status.set("Ready for import  |  One attachment at a time")

    def _browse(self, kind, types):
        path = filedialog.askopenfilename(
            parent=self.app, title=f"Select a {kind} file", initialdir=self.app.last_dir, filetypes=types)
        if not path:
            return
        self.app.last_dir = str(Path(path).parent)
        self.app.status.set(f"Selected {Path(path).name}  |  preview screen comes in the next slice", "ok")

    def _speak(self):
        self.app.status.set("Speech capture screen comes in a later slice", "warn")

    def _use_typed(self):
        text = self._typed_text()
        if not text.strip():
            self.app.status.set("Type or paste some text first", "warn")
            return
        self.app.status.set(f"Typed text ready ({len(text)} characters)  |  edit screen comes later", "ok")
