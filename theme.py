"""
theme.py — Shared "new-age spiritual" visual theme for Pradakshina Tracker.

Pure Kivy (no KivyMD dependency, to keep the Buildozer/APK build lightweight and fast).
Provides:
  - COLORS: warm saffron / maroon / gold / cream palette (+ dark mode variant)
  - GradientBackground: soft vertical gradient backdrop
  - GlassCard: rounded, softly-bordered "card" container
  - RoundButton: fully custom rounded button with press feedback (no default grey Kivy look)
  - ChipButton: small rounded pill button (used for quick-select targets)
  - HeadingLabel / SubLabel / BigStatLabel: consistent typography helpers
  - GlowPulse: helper to run a soft glow/pulse animation on any widget's canvas Color alpha
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.animation import Animation
from kivy.properties import ListProperty, NumericProperty, StringProperty

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COLORS = {
    "bg_top": (0.102, 0.098, 0.114, 1),      # deep charcoal-plum
    "bg_bottom": (0.055, 0.051, 0.067, 1),   # near-black base
    "card_bg": (0.145, 0.133, 0.153, 1),     # soft plum-grey glass panel
    "card_border": (1, 0.62, 0.28, 0.35),    # faint saffron edge
    "saffron": (1, 0.62, 0.28, 1),           # #FF9F45-ish
    "saffron_soft": (1, 0.62, 0.28, 0.18),
    "maroon": (0.60, 0.15, 0.23, 1),         # #7B1E3A-ish
    "maroon_deep": (0.42, 0.10, 0.16, 1),
    "gold": (0.83, 0.69, 0.22, 1),           # #D4AF37-ish
    "gold_bright": (1, 0.84, 0.25, 1),
    "cream": (0.98, 0.96, 0.94, 1),
    "text_primary": (0.97, 0.95, 0.93, 1),
    "text_muted": (0.72, 0.68, 0.70, 1),
    "success": (0.36, 0.78, 0.42, 1),
    "danger": (0.82, 0.30, 0.30, 1),
}


# ---------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------
class GradientBackground(Widget):
    """Soft vertical gradient backdrop, drawn as stacked bands (no extra deps)."""
    top_color = ListProperty(COLORS["bg_top"])
    bottom_color = ListProperty(COLORS["bg_bottom"])
    bands = NumericProperty(28)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)
        self.bind(top_color=self._redraw, bottom_color=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        n = self.bands
        band_h = self.height / n
        with self.canvas:
            for i in range(n):
                t = i / max(n - 1, 1)
                r = self.top_color[0] + (self.bottom_color[0] - self.top_color[0]) * t
                g = self.top_color[1] + (self.bottom_color[1] - self.top_color[1]) * t
                b = self.top_color[2] + (self.bottom_color[2] - self.top_color[2]) * t
                Color(r, g, b, 1)
                Rectangle(pos=(self.x, self.y + self.height - band_h * (i + 1)),
                          size=(self.width, band_h + 1))


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------
class GlassCard(BoxLayout):
    """A softly rounded 'glass' panel with a faint saffron border glow."""
    bg_color = ListProperty(COLORS["card_bg"])
    border_color = ListProperty(COLORS["card_border"])
    radius = NumericProperty(18)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color_inst = Color(*self.bg_color)
            self._bg_rect = RoundedRectangle(radius=[self.radius])
            self._border_color_inst = Color(*self.border_color)
            self._border_line = Line(width=1.2)
        self.bind(pos=self._update, size=self._update)
        self.bind(bg_color=self._update_colors, border_color=self._update_colors)

    def _update(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        r = self.radius
        self._border_line.rounded_rectangle = (
            self.x + 1, self.y + 1, self.width - 2, self.height - 2, r
        )

    def _update_colors(self, *args):
        self._bg_color_inst.rgba = self.bg_color
        self._border_color_inst.rgba = self.border_color


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
class RoundButton(Button):
    """Custom rounded button — no default Kivy grey box, warm palette + press feedback."""
    fill_color = ListProperty(COLORS["saffron"])
    text_color = ListProperty((1, 1, 1, 1))
    radius = NumericProperty(16)

    def __init__(self, **kwargs):
        # Strip Kivy's default button chrome entirely
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        super().__init__(**kwargs)
        self.color = self.text_color
        with self.canvas.before:
            self._color_inst = Color(*self.fill_color)
            self._rect = RoundedRectangle(radius=[self.radius])
        self.bind(pos=self._update, size=self._update, state=self._on_state,
                  fill_color=self._on_fill_color_change)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _on_fill_color_change(self, *args):
        if self.state != "down":
            self._color_inst.rgba = self.fill_color

    def _on_state(self, instance, value):
        if value == "down":
            r, g, b, a = self.fill_color
            self._color_inst.rgba = (r * 0.8, g * 0.8, b * 0.8, a)
        else:
            self._color_inst.rgba = self.fill_color


class GhostButton(RoundButton):
    """A lower-emphasis outline-style button (e.g. Cancel / Home)."""
    def __init__(self, **kwargs):
        kwargs.setdefault("fill_color", (1, 1, 1, 0.06))
        kwargs.setdefault("text_color", COLORS["text_muted"])
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLORS["card_border"])
            self._outline = Line(width=1)
        self.bind(pos=self._update_outline, size=self._update_outline)

    def _update_outline(self, *args):
        self._outline.rounded_rectangle = (
            self.x + 1, self.y + 1, self.width - 2, self.height - 2, self.radius
        )


class ChipButton(RoundButton):
    """Small pill-shaped quick-select chip (used on Set Target screen)."""
    selected = NumericProperty(0)  # 0 or 1, bool-like for Kivy property binding

    def __init__(self, **kwargs):
        kwargs.setdefault("fill_color", (1, 1, 1, 0.08))
        kwargs.setdefault("text_color", COLORS["text_primary"])
        kwargs.setdefault("radius", 24)
        super().__init__(**kwargs)

    def set_selected(self, is_selected: bool):
        self.selected = 1 if is_selected else 0
        if is_selected:
            self.fill_color = COLORS["saffron"]
            self.text_color = (1, 1, 1, 1)
        else:
            self.fill_color = (1, 1, 1, 0.08)
            self.text_color = COLORS["text_primary"]
        self.color = self.text_color
        self._on_fill_color_change()


# ---------------------------------------------------------------------------
# Typography helpers
# ---------------------------------------------------------------------------
class HeadingLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", "26sp")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("color", COLORS["saffron"])
        super().__init__(**kwargs)


class SubLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("color", COLORS["text_muted"])
        super().__init__(**kwargs)


class BigStatLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", "40sp")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("color", COLORS["gold_bright"])
        super().__init__(**kwargs)


# ---------------------------------------------------------------------------
# Glow / pulse animation helper
# ---------------------------------------------------------------------------
def pulse_widget_opacity(widget, low=0.55, high=1.0, duration=0.9, loop=True):
    """Runs a gentle breathing opacity pulse — used for glow rings & completion states."""
    anim = (Animation(opacity=high, duration=duration, t="in_out_sine") +
            Animation(opacity=low, duration=duration, t="in_out_sine"))
    if loop:
        anim.repeat = True
    anim.start(widget)
    return anim
