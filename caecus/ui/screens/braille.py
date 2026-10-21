from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.widgets import Card, primary_button, secondary_button


def to_braille(text):
    """TODO: ikabit dito ang braille translator ninyo. Dapat string ang ibalik."""
    raise NotImplementedError("braille translator is not connected yet")


class BrailleScreen(Screen):
    name = "braille"
    step = 4
    heading = "Braille conversion"
    subheading = "Review the braille output."

    def build(self):
        self._source, self._text_in = "", ""
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
        ctk.CTkLabel(head, text="Braille output", font=T.font(13), text_color=T.PRIMARY).grid(
            row=0, column=1, sticky="e")
        ctk.CTkFrame(card, fg_color=T.BORDER, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew")
        self.box = ctk.CTkTextbox(card, wrap="word", fg_color=T.CARD, text_color=T.TEXT,
                                  font=T.font(20), border_width=0)
        self.box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 10))

        self.actions.grid_columnconfigure(3, weight=1)
        secondary_button(self.actions, "< Back to edit", self._back, width=150).grid(row=0, column=0, padx=(0, 8))
        secondary_button(self.actions, "Copy", self._copy, width=100).grid(row=0, column=1, padx=(0, 8))
        secondary_button(self.actions, "Save braille...", self._save, width=160).grid(row=0, column=2)
        primary_button(self.actions, "Convert another", self._again, width=190).grid(row=0, column=4)

    def on_show(self, text="", source="", **ctx):
        self._source, self._text_in = source, text
        self.source_label.configure(text="" if source == "Typed text" else f"From {source}")
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        try:
            self.box.insert("1.0", to_braille(text))
            self.app.status.set("Braille conversion complete", "ok")
        except Exception as exc:
            self.box.insert("1.0", f"Could not convert to braille ({exc})")
            self.app.status.set(f"Braille conversion failed: {exc}"[:150], "error")
        self.box.see("1.0")

    def _braille(self):
        return self.box.get("1.0", "end-1c")

    def _back(self):
        self.app.show("edit", text=self._text_in, source=self._source)

    def _copy(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self._braille())
        self.app.update()
        self.app.status.set("Copied to clipboard", "ok")

    def _save(self):
        stem = Path(self._source).stem if self._source and self._source != "Typed text" else "caecus-braille"
        path = filedialog.asksaveasfilename(
            parent=self.app, title="Save braille", initialdir=self.app.last_dir, initialfile=f"{stem}.txt",
            defaultextension=".txt", filetypes=[("Text file", "*.txt"), ("Braille ready file", "*.brf")])
        if not path:
            return
        try:
            Path(path).write_text(self._braille(), encoding="utf-8")
        except OSError as exc:
            self.app.status.set(f"Could not save: {exc}"[:150], "error")
            return
        self.app.last_dir = str(Path(path).parent)
        self.app.status.set(f"Saved {Path(path).name}", "ok")

    def _again(self):
        self.app.show("attach")