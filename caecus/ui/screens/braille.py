from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import re

from caecus.ui import theme as T
from caecus.ui.screens.base import Screen
from caecus.ui.widgets import Card, primary_button, secondary_button

from caecus.ui import embosser
from caecus.ui.embosser import CELLS_PER_LINE, LINES_PER_PAGE

_LET = dict(zip("abcdefghijklmnopqrstuvwxyz", "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"))
_NUM = dict(zip("1234567890", "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚"))
_PUNCT = {",": "⠂", ";": "⠆", ":": "⠒", ".": "⠲", "!": "⠖", "?": "⠦", "'": "⠄", "’": "⠄", "‘": "⠄",
          "-": "⠤", "–": "⠠⠤", "—": "⠐⠠⠤", "(": "⠐⠣", ")": "⠐⠜", "“": "⠦", "”": "⠴",
          "/": "⠸⠌", "…": "⠲⠲⠲"}
_NUMBER_SIGN, _CAPITAL, _CAPITAL_WORD, _LETTER_SIGN = "⠼", "⠠", "⠠⠠", "⠰"


GRADE = "Grade 1"


def layout_stats(braille):
    """Cells, lines and pages if the text is word-wrapped at CELLS_PER_LINE."""
    cells = len(braille.replace("\n", ""))
    lines = 0
    for para in braille.split("\n"):
        lines += 1
        cur = 0
        for word in para.split(" "):
            n = len(word)
            if cur == 0:
                cur = n
            elif cur + 1 + n <= CELLS_PER_LINE:
                cur += 1 + n
            else:
                lines += 1
                cur = n
            while cur > CELLS_PER_LINE:  # salitang mas mahaba pa sa isang linya
                lines += 1
                cur -= CELLS_PER_LINE
    pages = max(1, -(-lines // LINES_PER_PAGE))
    return cells, lines, pages

def to_braille(text):
    
    """TODO: input Braille translator here!. String output"""
     #raise NotImplementedError("braille translator is not connected yet")
    """Basic Grade 1 (uncontracted) English braille, as Unicode braille characters."""
    out, in_number = [], False
    tokens = re.findall(r"[A-Za-z]+|\d|\s|.", text, flags=re.S)
    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i else ""
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if tok[0].isalpha() and tok.isascii():
            if in_number and tok[0].lower() in "abcdefghij":
                out.append(_LETTER_SIGN)  # a-j right after a number would read as digits
            in_number = False
            if len(tok) > 1 and tok.isupper():
                out.append(_CAPITAL_WORD)
                out.append("".join(_LET[c] for c in tok.lower()))
            else:
                out.append("".join((_CAPITAL if c.isupper() else "") + _LET[c.lower()] for c in tok))
        elif tok in _NUM:
            if not in_number:
                out.append(_NUMBER_SIGN)
                in_number = True
            out.append(_NUM[tok])
        elif tok in (".", ",") and in_number and nxt in _NUM:
            out.append(_PUNCT[tok])  # decimal point / thousands comma stays in the number
        elif tok == '"':
            in_number = False
            opening = (not prev) or prev.isspace() or prev in "([{"
            out.append("⠦" if opening else "⠴")
        else:
            in_number = False
            out.append(_PUNCT.get(tok, tok))  # spaces/newlines pass through; unknown symbols stay as-is
    return "".join(out)

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
        self.output_label = ctk.CTkLabel(head, text="Braille output", font=T.font(13), text_color=T.PRIMARY)
        self.output_label.grid(row=0, column=1, sticky="e")


        ctk.CTkFrame(card, fg_color=T.BORDER, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew")
        self.box = ctk.CTkTextbox(card, wrap="word", fg_color=T.CARD, text_color=T.TEXT,
                                  font=T.font(20), border_width=0)
        self.box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 10))

        self._ok = False
        self.box.bind("<KeyRelease>", lambda _e: self._update_info())
        
        self.actions.grid_columnconfigure(3, weight=1)
        secondary_button(self.actions, "< Back to edit", self._back, width=150).grid(row=0, column=0, padx=(0, 8))
        secondary_button(self.actions, "Copy", self._copy, width=100).grid(row=0, column=1, padx=(0, 8))
        secondary_button(self.actions, "Save braille...", self._save, width=160).grid(row=0, column=2)
        self.print_btn = primary_button(self.actions, "Print", self._print, width=120)
        self.print_btn.grid(row=0, column=4, padx=(0, 8))
        secondary_button(self.actions, "Convert another", self._again, width=170).grid(row=0, column=5)

    def on_show(self, text="", source="", **ctx):
        self._source, self._text_in = source, text
        self.source_label.configure(text="" if source == "Typed text" else f"From {source}")
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        try:
            self.box.insert("1.0", to_braille(text))
            self._ok = True
            self.app.status.set("Braille conversion complete", "ok")
        except Exception as exc:
            self._ok = False
            self.box.insert("1.0", f"Could not convert to braille ({exc})")
            self.app.status.set(f"Braille conversion failed: {exc}"[:150], "error")
        self._update_info()
        self.box.see("1.0")

    def _update_info(self):
        if not self._ok:
            self.output_label.configure(text="Braille output")
            return
        cells, lines, pages = layout_stats(self._braille())
        self.output_label.configure(
            text=f"Braille output  |  {GRADE}  |  {cells} cells  |  {lines} lines  |  "
                 f"{pages} page{'s' if pages != 1 else ''}")

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

    def _print(self):
        text = self._braille()
        if not self._ok or not text.strip():
            self.app.status.set("Nothing to print", "warn")
            return
        pages = embosser.paginate(text)
        n = len(pages)
        label = f"{n} page{'s' if n != 1 else ''}"
        try:
            embosser.send_pages(pages)
        except embosser.EmbosserError as exc:
            self.app.status.set(f"Cannot print ({label} ready): {exc}"[:150], "warn")
            return
        except Exception as exc:
            self.app.status.set(f"Print failed: {exc}"[:150], "error")
            return
        self.app.status.set(f"Sent {label} to the embosser", "ok")