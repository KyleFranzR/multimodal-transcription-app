"""Design tokens approximated from the Figma 'Caecus-app' frames (800x480)."""
import tkinter.font as tkfont

import customtkinter as ctk

DESIGN_W, DESIGN_H = 800, 480
SCALE = 1.0  # set by the app once the screen size is known

BG = "#F3F5F8"
BAR = "#E9EDF2"
CARD = "#FFFFFF"
BORDER = "#D9DFE7"
PRIMARY = "#2362B3"
PRIMARY_HOVER = "#1B4E91"
PRIMARY_TINT = "#E8F0FA"
TEXT = "#1F2933"
MUTED = "#5F6B7A"
FAINT = "#8A94A3"
MARKER_OFF = "#E3E8EE"
DANGER = "#B83A3A"
WARN = "#B7791F"
OK = "#2F855A"
DISABLED_TEXT = "#A9B2BE"

FAMILY_PREFERENCE = ("OpenDyslexic", "Inter", "DejaVu Sans")
_family = None
_tk_fonts = {}


def init(root):
    """Pick the UI font. Call once, after the root window exists."""
    global _family
    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()
    _family = next((f for f in FAMILY_PREFERENCE if f in available), None)
    print(f"UI font: {_family or 'default'}")
    return _family


def font(size, weight="normal"):
    if _family:
        return ctk.CTkFont(family=_family, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)


def tk_font(size, weight="normal"):
    """Plain Tk font for canvas drawing (sizes in design pixels, scaled here)."""
    key = (size, weight)
    if key not in _tk_fonts:
        family = _family or tkfont.nametofont("TkDefaultFont").actual("family")
        _tk_fonts[key] = tkfont.Font(family=family, size=-max(1, round(size * SCALE)), weight=weight)
    return _tk_fonts[key]
