from kivy.uix.widget import Widget
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Ellipse, Line
from kivy.properties import NumericProperty
from kivy.animation import Animation

from theme import COLORS


class RotatingCompassWidget(Widget):
    """
    Circular compass + progress-ring centerpiece for the Live Tracking screen.

    - heading: 0-360, purely driven by sensor-fused data from PradakshinaDetector.
      Rotates the inner needle/marker smoothly (never manually draggable).
    - progress: 0.0-1.0, fraction of the target lap count completed. Fills an
      outer arc ring (like a loading/achievement ring) around the compass.
    - pulse(): call once when a lap completes, for a quick gold flash feedback.
    """
    heading = NumericProperty(0)
    progress = NumericProperty(0.0)  # 0..1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            # Outer track (dim full circle) behind the progress arc
            Color(1, 1, 1, 0.08)
            self.track_ring = Line(width=6)

            # Progress arc — fills as laps approach the target
            Color(*COLORS["gold_bright"])
            self.progress_ring = Line(width=6, cap='round')

            # Soft inner glass disc
            Color(*COLORS["card_bg"])
            self.inner_disc = Ellipse()

            # Flash overlay for lap-complete pulse (starts invisible)
            self._flash_color = Color(1, 0.85, 0.3, 0.0)
            self.flash_ring = Line(width=10)

            PushMatrix()
            self.rotation = Rotate(angle=0, origin=self.center)

        with self.canvas:
            # Saffron compass ring (rotates with heading)
            Color(*COLORS["saffron"])
            self.outer_ring = Line(width=2)

            # Gold needle pointer (rotates — represents live walking heading)
            Color(*COLORS["gold_bright"])
            self.direction_pointer = Line(width=4, cap='round')

        with self.canvas.after:
            PopMatrix()
            # Fixed sanctum-center marker (does NOT rotate — represents temple center)
            Color(*COLORS["maroon"])
            self.center_dot = Ellipse()
            Color(1, 1, 1, 0.9)
            self.center_dot_ring = Line(width=1.5)

        self.bind(pos=self._update_geometry, size=self._update_geometry)
        self.bind(heading=self._on_heading_change, progress=self._update_geometry)

    def _update_geometry(self, *args):
        self.rotation.origin = self.center
        radius = min(self.width, self.height) * 0.42
        if radius <= 0:
            return

        # Outer dim track (full circle)
        self.track_ring.circle = (self.center_x, self.center_y, radius + 14)

        # Progress arc: starts at 90 (top) and sweeps clockwise based on progress
        pct = max(0.0, min(1.0, self.progress))
        start_angle = 90
        end_angle = 90 - (360 * pct)  # clockwise sweep
        self.progress_ring.circle = (
            self.center_x, self.center_y, radius + 14, end_angle, start_angle
        )

        # Inner glass disc
        inner_r = radius * 0.78
        self.inner_disc.pos = (self.center_x - inner_r, self.center_y - inner_r)
        self.inner_disc.size = (inner_r * 2, inner_r * 2)

        # Rotating saffron ring + needle (heading indicator)
        self.outer_ring.circle = (self.center_x, self.center_y, radius)
        self.direction_pointer.points = [
            self.center_x, self.center_y,
            self.center_x, self.center_y + radius * 0.85
        ]

        # Flash ring (same radius as outer ring)
        self.flash_ring.circle = (self.center_x, self.center_y, radius)

        # Fixed sanctum-center dot
        dot_r = 10
        self.center_dot.pos = (self.center_x - dot_r, self.center_y - dot_r)
        self.center_dot.size = (dot_r * 2, dot_r * 2)
        self.center_dot_ring.circle = (self.center_x, self.center_y, dot_r + 3)

    def _on_heading_change(self, instance, new_heading):
        # Smooth interpolation to prevent jittering; handles 359->0 wraparound correctly.
        current = self.rotation.angle % 360
        target = new_heading % 360
        diff = (target - current + 180) % 360 - 180
        Animation.cancel_all(self.rotation)
        Animation(angle=self.rotation.angle + diff, duration=0.15, t='out_quad').start(self.rotation)

    def pulse(self):
        """Brief golden flash — call when a single lap completes."""
        Animation.cancel_all(self._flash_color)
        self._flash_color.a = 0.9
        Animation(a=0.0, duration=0.6, t='out_quad').start(self._flash_color)
