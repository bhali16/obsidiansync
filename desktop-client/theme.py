"""Color palette and custom-drawn widgets for the ObsidianSync desktop UI.

Ported from the Claude-designed artifact (redesign-code/ObsidianSync.dc.html), which used
oklch() colors on the web; here they're approximated as hex since tkinter has no oklch support.
"""
import math
import tkinter as tk
from tkinter import font as tkfont

FONT_FAMILY = "Helvetica Neue"
MONO_FAMILY = "Menlo"

BODY_BG = "#17151d"
CARD_BG = "#1d1b24"
TEXT = "#f1f0f4"
SUBTEXT = "#a8a6b3"
MUTED = "#716f7d"

ACCENT = "#a78bfa"
ACCENT_2 = "#9350dd"
ACCENT_HOVER = "#9575f0"
ACCENT_TEXT = "#ffffff"

ICON_BTN_BG = "#322f3b"
ICON_BTN_HOVER = "#3d3949"
ICON_COLOR = "#d9d7de"

MODAL_SCRIM = "#0a0a0e"
MODAL_BG = "#242230"
MODAL_CLOSE_BG = "#37333f"
FIELD_BG = "#19171f"
FIELD_BORDER = "#3a3646"
GHOST_BTN_BG = "#302c3b"
GHOST_BTN_HOVER = "#3a3548"

SUCCESS = "#4ade80"
ERROR = "#f0725a"

# Per-state colors for the top-right status pill: (background, dot, text)
STATUS_COLORS = {
    "waiting": ("#37333f", "#8f8d96", "#d9d7de"),
    "connected": ("#3a3350", ACCENT, "#ece7fb"),
    "syncing": ("#423460", ACCENT, "#ebe6f5"),
    "complete": ("#2c4a3a", SUCCESS, "#e3f7ec"),
    "error": ("#4a2e28", ERROR, "#fbe8e3"),
}

HELPER_TEXT = {
    "waiting": "Open the ObsidianSync app on your Android device and scan this code to connect.",
    "connected": "Device connected. Start the sync from your phone whenever you're ready.",
    "syncing": "Keep both devices on the same Wi-Fi network until the sync finishes.",
    "complete": "Your vault and your device now match. Safe to disconnect.",
    "error": "The device dropped off the network. Check Wi-Fi and try again.",
}


def draw_rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class Pill(tk.Canvas):
    """A rounded, colored status badge with a dot + text label, auto-sized to its text."""

    def __init__(self, parent, text: str, state: str = "waiting", height=32, parent_bg=CARD_BG):
        super().__init__(parent, height=height, bg=parent_bg, highlightthickness=0)
        self._height = height
        self._font = (FONT_FAMILY, 12, "bold")
        self.render(text, state)

    def render(self, text: str, state: str):
        bg, dot, fg = STATUS_COLORS.get(state, STATUS_COLORS["waiting"])
        measurer = tkfont.Font(family=self._font[0], size=self._font[1], weight="bold")
        width = 16 + 8 + 4 + 8 + measurer.measure(text) + 16
        self.configure(width=width)
        self.delete("all")
        draw_rounded_rect(self, 0, 0, width, self._height, radius=self._height // 2, fill=bg, outline="")
        cx, cy = 16, self._height // 2
        r = 4
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=dot, outline="")
        self.create_text(cx + r + 8, cy, text=text, anchor="w", fill=fg, font=self._font)


class IconButton(tk.Canvas):
    """A small rounded square button showing a glyph (used for the Activity / Settings icons)."""

    def __init__(self, parent, glyph: str, command=None, size=40, parent_bg=CARD_BG):
        super().__init__(parent, width=size, height=size, bg=parent_bg, highlightthickness=0,
                          cursor="pointinghand")
        self.command = command
        self._size = size
        self._draw(ICON_BTN_BG, glyph)
        self.bind("<Enter>", lambda _e: self._draw(ICON_BTN_HOVER, glyph))
        self.bind("<Leave>", lambda _e: self._draw(ICON_BTN_BG, glyph))
        self.bind("<Button-1>", lambda _e: self.command() if self.command else None)
        self._glyph = glyph

    def _draw(self, color, glyph):
        self.delete("all")
        draw_rounded_rect(self, 0, 0, self._size, self._size, radius=12, fill=color, outline="")
        self.create_text(self._size / 2, self._size / 2, text=glyph, fill=ICON_COLOR,
                          font=(FONT_FAMILY, 16))


class RoundedButton(tk.Canvas):
    """A clickable pill/rounded-rect button with real rounded corners (ttk cannot do this)."""

    def __init__(
        self, parent, text: str, command=None,
        bg=ACCENT, hover_bg=ACCENT_HOVER, fg=ACCENT_TEXT,
        width=160, height=40, radius=20, font=None, parent_bg=CARD_BG,
    ):
        super().__init__(parent, width=width, height=height, bg=parent_bg, highlightthickness=0,
                          cursor="pointinghand")
        self.command = command
        self.bg_color = bg
        self.hover_bg = hover_bg
        self.fg_color = fg
        self._width = width
        self._height = height
        self._radius = radius
        self._font = font or (FONT_FAMILY, 13, "bold")
        self._text = text
        self._enabled = True

        self._draw(self.bg_color)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self._width = event.width
        self._height = event.height
        self._draw(self._current_color)

    def _draw(self, color):
        self._current_color = color
        self.delete("all")
        draw_rounded_rect(
            self, 1, 1, self._width - 1, self._height - 1,
            radius=min(self._radius, self._height / 2), fill=color, outline=""
        )
        text_color = self.fg_color if self._enabled else MUTED
        self.create_text(self._width / 2, self._height / 2, text=self._text,
                          fill=text_color, font=self._font)

    def _on_enter(self, _event):
        if self._enabled:
            self._draw(self.hover_bg)

    def _on_leave(self, _event):
        self._draw(self.bg_color)

    def _on_click(self, _event):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.configure(cursor="pointinghand" if enabled else "arrow")
        self._draw(self.bg_color)


class Spinner(tk.Canvas):
    """An indeterminate spinning ring, drawn as a rotating arc (used in the 'syncing' panel)."""

    def __init__(self, parent, size=64, track=None, active=ACCENT, parent_bg=CARD_BG):
        super().__init__(parent, width=size, height=size, bg=parent_bg, highlightthickness=0)
        self._size = size
        self._track = track or "#3c3947"
        self._active = active
        self._angle = 0
        self._running = False
        self._after_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        pad = 5
        self.create_oval(pad, pad, self._size - pad, self._size - pad,
                          outline=self._track, width=5)
        self.create_arc(pad, pad, self._size - pad, self._size - pad,
                         start=self._angle, extent=70, style="arc",
                         outline=self._active, width=5)

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def _tick(self):
        if not self._running:
            return
        self._angle = (self._angle - 12) % 360
        self._draw()
        self._after_id = self.after(60, self._tick)

    def stop(self):
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None


def draw_check_circle(canvas: tk.Canvas, cx, cy, r, ring_color, mark_color="white"):
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=ring_color, outline="")
    s = r * 0.5
    canvas.create_line(cx - s, cy, cx - s * 0.2, cy + s * 0.7, cx + s, cy - s * 0.6,
                        fill=mark_color, width=int(r * 0.14), capstyle="round", joinstyle="round")


def draw_warning_circle(canvas: tk.Canvas, cx, cy, r, ring_color, mark_color="white"):
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=ring_color, outline="")
    w = max(2, int(r * 0.14))
    canvas.create_line(cx, cy - r * 0.45, cx, cy + r * 0.12, fill=mark_color, width=w, capstyle="round")
    canvas.create_oval(cx - w / 2, cy + r * 0.32, cx + w / 2, cy + r * 0.32 + w,
                        fill=mark_color, outline="")
