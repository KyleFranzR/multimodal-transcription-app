import customtkinter as ctk


class Screen(ctk.CTkFrame):
    """One wizard screen: a workspace on top and an action bar below it."""

    name = ""
    heading = ""
    subheading = ""
    step = 1

    def __init__(self, app):
        super().__init__(app.container, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.grid(row=0, column=0, sticky="nsew", padx=16)
        self.actions = ctk.CTkFrame(self, fg_color="transparent", height=44)
        self.actions.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        self.build()

    def build(self):
        pass

    def on_show(self, **ctx):
        pass

    def on_hide(self):
        pass
