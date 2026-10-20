import os
from pathlib import Path

import customtkinter as ctk

from caecus.ui import theme as T
from caecus.ui.services import Transcriber
from caecus.ui.screens.attach import AttachScreen
from caecus.ui.screens.edit import EditScreen
from caecus.ui.screens.preview import PreviewScreen
from caecus.ui.widgets import StatusBar, StepProgress

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class CaecusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        T.init(self)
        self.title("Caecus")
        self.configure(fg_color=T.BG)
        T.SCALE = max(1.0, self.winfo_screenheight() / T.DESIGN_H)
        ctk.set_widget_scaling(T.SCALE)
        self.last_dir = str(Path.home())
        self.transcriber = Transcriber()

        # Kiosk fullscreen must be applied after CTk finishes window setup.
        geometry = os.environ.get("CAECUS_GEOMETRY")  # e.g. 1024x600 for a windowed test
        if geometry:
            self.geometry(geometry)
        else:
            self.after(1000, lambda: self.attributes("-fullscreen", True))
        self.bind("<Control-Alt-q>", lambda _e: self.destroy())

        self._build_chrome()
        self.screens = {}
        for cls in (AttachScreen, PreviewScreen, EditScreen):
            self.screens[cls.name] = cls(self)
        self._current = None
        self.show("attach")
        self.after(1500, self._repaint)
        self.transcriber.start_loading()
        self.after(300, self._check_asr)

    def _build_chrome(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(self, fg_color=T.BAR, corner_radius=0, height=44)
        bar.grid(row=0, column=0, sticky="ew")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="Caecus", font=T.font(16, "bold"), text_color=T.TEXT).pack(
            side="left", padx=16)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 8))
        head.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        self.heading_label = ctk.CTkLabel(titles, text="", font=T.font(24, "bold"),
                                          text_color=T.TEXT, anchor="w")
        self.heading_label.pack(anchor="w")
        self.subheading_label = ctk.CTkLabel(titles, text="", font=T.font(13),
                                             text_color=T.MUTED, anchor="w")
        self.subheading_label.pack(anchor="w")
        self.progress = StepProgress(head)
        self.progress.grid(row=0, column=1, sticky="e")

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=2, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        ctk.CTkFrame(self, fg_color=T.BORDER, height=1, corner_radius=0).grid(row=3, column=0, sticky="ew")
        self.status = StatusBar(self)
        self.status.grid(row=4, column=0, sticky="ew")

    def show(self, name, **ctx):
        if self._current is not None:
            self._current.grid_remove()
            self._current.on_hide()
        screen = self.screens[name]
        screen.grid(row=0, column=0, sticky="nsew")
        self._current = screen
        screen.on_show(**ctx)
        self.heading_label.configure(text=screen.heading)
        self.subheading_label.configure(text=screen.subheading)
        self.progress.set_step(screen.step)
        self.repaint_soon()

    def _check_asr(self):
        if self.transcriber.asr_state in ("idle", "loading"):
            self.after(300, self._check_asr)
        elif self._current is not None and self._current.name == "attach":
            self._current.refresh_status()

    def repaint_soon(self):
        self.after(60, self._repaint)

    def _repaint(self):
        """Workaround: CTkLabel text is not painted on first draw (seen on the Pi with CTk 6.0)."""
        labels = []

        def walk(widget):
            if isinstance(widget, ctk.CTkLabel):
                labels.append((widget, widget.cget("text")))
            for child in widget.winfo_children():
                walk(child)

        walk(self)
        for widget, text in labels:
            widget.configure(text=text + "\u200b")
        self.update_idletasks()
        for widget, text in labels:
            widget.configure(text=text)
        self.update_idletasks()


def main():
    CaecusApp().mainloop()


if __name__ == "__main__":
    main()
