import tkinter as tk

import customtkinter as ctk

from caecus.ui import theme as T


class Card(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        kw.setdefault("fg_color", T.CARD)
        super().__init__(parent, border_color=T.BORDER, border_width=1, corner_radius=8, **kw)


def primary_button(parent, text, command, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command, height=44, corner_radius=8,
        fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOVER, text_color="#FFFFFF",
        text_color_disabled=T.DISABLED_TEXT, font=T.font(15, "bold"), **kw)


def secondary_button(parent, text, command, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command, height=44, corner_radius=8,
        fg_color=T.CARD, hover_color=T.PRIMARY_TINT, text_color=T.TEXT,
        text_color_disabled=T.DISABLED_TEXT, border_width=1, border_color=T.BORDER,
        font=T.font(15, "bold"), **kw)


def make_tappable(command, card, *children):
    """Make a card (and the labels inside it) act as one big touch button."""
    def press(_event):
        card.configure(fg_color=T.PRIMARY_TINT)

    def release(_event):
        card.configure(fg_color=T.CARD)
        command()

    for widget in (card, *children):
        widget.bind("<ButtonPress-1>", press, add="+")
        widget.bind("<ButtonRelease-1>", release, add="+")


class Marker(tk.Canvas):
    """Round numbered step marker, drawn by hand (tiny CTk rounded widgets mis-paint on the Pi)."""

    SIZE = 22

    def __init__(self, parent, number):
        px = int(self.SIZE * T.SCALE)
        super().__init__(parent, width=px, height=px, bg=T.BG, highlightthickness=0, bd=0)
        self._oval = self.create_oval(1, 1, px - 1, px - 1, outline="", fill=T.MARKER_OFF)
        self._text = self.create_text(px / 2, px / 2, text=str(number), fill=T.MUTED,
                                      font=T.tk_font(12, "bold"))

    def set_active(self, active):
        self.itemconfigure(self._oval, fill=T.PRIMARY if active else T.MARKER_OFF)
        self.itemconfigure(self._text, fill="#FFFFFF" if active else T.MUTED)


class Dot(tk.Canvas):
    def __init__(self, parent, bg, color=T.PRIMARY, size=6):
        px = max(4, int(size * T.SCALE))
        super().__init__(parent, width=px, height=px, bg=bg, highlightthickness=0, bd=0)
        self._oval = self.create_oval(0, 0, px - 1, px - 1, outline="", fill=color)

    def set_color(self, color):
        self.itemconfigure(self._oval, fill=color)


class StepProgress(ctk.CTkFrame):
    LABELS = ("Attach", "Preview", "Edit text")

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._markers, self._labels = [], []
        for i, name in enumerate(self.LABELS):
            marker = Marker(self, i + 1)
            label = ctk.CTkLabel(self, text=name, font=T.font(13))
            marker.grid(row=0, column=2 * i,
                        padx=(0 if i == 0 else int(12 * T.SCALE), int(6 * T.SCALE)))
            label.grid(row=0, column=2 * i + 1)
            self._markers.append(marker)
            self._labels.append(label)
        self.set_step(1)

    def set_step(self, step):
        for i, (marker, label) in enumerate(zip(self._markers, self._labels), start=1):
            marker.set_active(i == step)
            if i == step:
                label.configure(text_color=T.PRIMARY, font=T.font(13, "bold"))
            else:
                label.configure(text_color=T.MUTED, font=T.font(13))


class StatusBar(ctk.CTkFrame):
    COLORS = {"info": T.PRIMARY, "ok": T.OK, "warn": T.WARN, "error": T.DANGER}

    def __init__(self, parent):
        super().__init__(parent, fg_color=T.BAR, corner_radius=0)
        self._dot = Dot(self, bg=T.BAR)
        self._dot.pack(side="left", padx=(int(16 * T.SCALE), int(6 * T.SCALE)))
        self._label = ctk.CTkLabel(self, text="", font=T.font(12), text_color=T.MUTED, anchor="w")
        self._label.pack(side="left", fill="x", expand=True, pady=2)

    def set(self, text, level="info"):
        self._dot.set_color(self.COLORS.get(level, T.PRIMARY))
        self._label.configure(text=text)
