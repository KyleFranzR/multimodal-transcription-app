from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.widgets import Card, primary_button, secondary_button
from caecus.ui.widgets import Card, enable_undo, primary_button, secondary_button

class EditScreen(Screen):
    name = "edit"
    step = 3
    heading = "Review and edit text"
    subheading = "Check the text and make any changes you need."

    def build(self):
        self._source = ""
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
        self.source_label = ctk.CTkLabel(head, text="", font=T.font(13), text_color=T.MUTED, anchor="w")
        self.source_label.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(head, text="Editable text", font=T.font(13), text_color=T.PRIMARY).grid(
            row=0, column=1, sticky="e")
        ctk.CTkFrame(card, fg_color=T.BORDER, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew")
        self.box = ctk.CTkTextbox(card, wrap="word", fg_color=T.CARD, text_color=T.TEXT,
                                  font=T.font(16), border_width=0)
        self.box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 10))
        enable_undo(self.box)

        self.actions.grid_columnconfigure(2, weight=1)
        secondary_button(self.actions, "Copy", self._copy, width=100).grid(row=0, column=0, padx=(0, 8))
        secondary_button(self.actions, "Save text...", self._save, width=150).grid(row=0, column=1)
        ctk.CTkLabel(self.actions, text="Return to Import / attach", font=T.font(13),
            text_color=T.MUTED).grid(row=0, column=3, padx=(0, 12))
        primary_button(self.actions, "Convert to braille", self._to_braille, width=190).grid(
            row=0, column=4, padx=(0, 8))
        secondary_button(self.actions, "Convert another", self._again, width=170).grid(row=0, column=5)

    def on_show(self, text="", source="", **ctx):
        self._source = source
        self.source_label.configure(text=source if source == "Typed text" else f"From {source}")
        self.box.delete("1.0", "end")
        self.box.insert("1.0", text)
        self.box.edit_reset()  # no undo after load
        self.box.see("1.0")
        if source == "Typed text":
            self.app.status.set("Text ready  |  Convert another returns to Import / attach", "ok")
        else:
            self.app.status.set("Conversion complete  |  Convert another returns to Import / attach", "ok")

    def _text(self):
        return self.box.get("1.0", "end-1c")

    def _copy(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self._text())
        self.app.update()
        self.app.status.set("Copied to clipboard", "ok")

    def _save(self):
        stem = Path(self._source).stem if self._source and self._source != "Typed text" else "caecus-text"
        path = filedialog.asksaveasfilename(
            parent=self.app, title="Save text", initialdir=self.app.last_dir, initialfile=f"{stem}.txt",
            defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if not path:
            return
        try:
            Path(path).write_text(self._text(), encoding="utf-8")
        except OSError as exc:
            self.app.status.set(f"Could not save: {exc}"[:150], "error")
            return
        self.app.last_dir = str(Path(path).parent)
        self.app.status.set(f"Saved {Path(path).name}", "ok")

    def _again(self):
        self.app.show("attach")

    def _to_braille(self):
        text = self._text()
        if not text.strip():
            self.app.status.set("Nothing to convert to braille", "warn")
            return
        self.app.show("braille", text=text, source=self._source)
