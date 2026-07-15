"""
pradakshina_detector.py — Core lap-detection logic.

Accuracy improvements over the previous version:
  1. Uses the ACTUAL elapsed time between update() calls (Kivy Clock's dt) to integrate
     heading, instead of assuming every tick is exactly 100ms. Clock ticks drift under load
     (device rendering a busy screen, GC pauses, etc.) — assuming a fixed dt silently
     mis-integrates the heading over a multi-minute session.
  2. Step detection uses an ADAPTIVE threshold (rolling mean + k*std of the recent filtered
     accelerometer magnitude) rather than one fixed number for every user. A brisk young
     devotee and a slow elderly devotee produce very different accelerometer signatures;
     a single fixed threshold is either too sensitive for one or too blind for the other.
  3. Heading integration is delegated to SensorService.get_fused_heading_delta_degrees(),
     which already combines gyroscope + compass to resist drift — the detector no longer
     touches raw gyro values directly.
  4. Tracks a per-lap CONFIDENCE score (0-1) based on step-interval regularity and heading
     smoothness, so the app can flag a likely-noisy lap for the devotee to manually verify
     rather than silently presenting it as certain. This is reported honestly rather than
     hard-coded to a flat 0.9 as before.

Honest limits: this still cannot reach "100% accuracy" — no consumer MEMS sensor pipeline
can — but this is the realistic ceiling for phone-only sensing, and manual +/- correction
remains available in the UI for exactly this reason.
"""

import time
import math
from collections import deque


class PradakshinaDetector:
    def __init__(self, sensor_service, on_lap_complete, on_step_detected=None):
        self.sensor_service = sensor_service
        self.on_lap_complete = on_lap_complete
        self.on_step_detected = on_step_detected

        self.walking = False
        self.cumulative_heading = 0.0
        self.last_step_time = None
        self.step_gap_min_ms = 250   # ignore triggers faster than this (debounce / noise)
        self.step_gap_max_ms = 2500  # if quieter than this, assume the devotee has stopped
        self.heading_threshold_deg = 350.0
        self.step_count = 0
        self.is_active = False

        # Rolling window of recent filtered accelerometer magnitudes, used to compute an
        # adaptive (per-user, per-session) step threshold instead of one fixed constant.
        self._magnitude_history = deque(maxlen=30)
        self._min_step_threshold = 1.0   # floor, so a near-silent signal never false-triggers
        self._max_step_threshold = 3.5   # ceiling, so a single violent jolt doesn't set the bar absurdly high

        # Per-lap confidence tracking
        self._step_intervals_this_lap = deque(maxlen=60)
        self._heading_deltas_this_lap = deque(maxlen=200)
        self.last_lap_confidence = 1.0
        self.session_confidences = []

        self._last_update_time = None

    def start(self):
        self.is_active = True
        self.walking = False
        self.cumulative_heading = 0.0
        self.last_step_time = None
        self.step_count = 0
        self._magnitude_history.clear()
        self._step_intervals_this_lap.clear()
        self._heading_deltas_this_lap.clear()
        self.session_confidences = []
        self._last_update_time = None
        self.sensor_service.start_sensors()

    def stop(self):
        self.is_active = False
        self.sensor_service.stop_sensors()

    def _current_step_threshold(self) -> float:
        """Adaptive threshold = recent mean + 1.3 standard deviations, clamped to sane bounds."""
        if len(self._magnitude_history) < 5:
            return 1.4  # sane default until we've accumulated enough samples to adapt
        n = len(self._magnitude_history)
        mean = sum(self._magnitude_history) / n
        variance = sum((x - mean) ** 2 for x in self._magnitude_history) / n
        std = math.sqrt(variance)
        threshold = mean + 1.3 * std
        return max(self._min_step_threshold, min(self._max_step_threshold, threshold))

    def update(self, in_geofence: bool, dt: float = 0.1):
        if not self.is_active or not in_geofence:
            self._reset_tracking_state()
            return

        now_ms = time.time() * 1000

        # 1. Adaptive step detection
        filtered_mag = self.sensor_service.get_filtered_accel_magnitude()
        self._magnitude_history.append(abs(filtered_mag))
        threshold = self._current_step_threshold()

        step_detected = (
            abs(filtered_mag) > threshold
            and (self.last_step_time is None or now_ms - self.last_step_time > self.step_gap_min_ms)
        )

        if step_detected:
            if self.last_step_time is not None:
                self._step_intervals_this_lap.append(now_ms - self.last_step_time)
            self.last_step_time = now_ms
            self.walking = True
            self.step_count += 1
            if self.on_step_detected:
                self.on_step_detected(self.step_count)
        elif self.last_step_time and now_ms - self.last_step_time > self.step_gap_max_ms:
            # Devotee has paused (praying, prostrating) — pause rotation tracking, don't reset.
            self.walking = False

        # 2. Heading integration — real elapsed dt, fused gyro+compass from SensorService.
        # Guard dt to a sane range in case of a stalled frame or a very first call.
        safe_dt = min(max(dt, 0.001), 1.0)
        heading_delta = self.sensor_service.get_fused_heading_delta_degrees(safe_dt)

        if self.walking:
            self.cumulative_heading += heading_delta
            self._heading_deltas_this_lap.append(heading_delta)

        # 3. Check for full rotation
        if abs(self.cumulative_heading) >= self.heading_threshold_deg:
            self.last_lap_confidence = self._compute_lap_confidence()
            self.session_confidences.append(self.last_lap_confidence)
            self.on_lap_complete()

            # Keep the remainder rather than hard-resetting, so the compass needle keeps
            # spinning continuously through the reset point instead of visibly snapping.
            if self.cumulative_heading > 0:
                self.cumulative_heading -= 360.0
            else:
                self.cumulative_heading += 360.0

            self._step_intervals_this_lap.clear()
            self._heading_deltas_this_lap.clear()

    def _compute_lap_confidence(self) -> float:
        """
        A simple, explainable confidence score (0-1) — not a black box — based on two things
        a devotee/temple admin could sanity-check themselves:
          - step regularity: consistent stride timing looks like real walking, not noise
          - heading smoothness: a real walked lap accumulates fairly steadily, not in a few
            huge jumps (which would suggest sensor glitch or the phone spinning in a pocket)
        """
        score = 1.0

        if len(self._step_intervals_this_lap) >= 3:
            mean_interval = sum(self._step_intervals_this_lap) / len(self._step_intervals_this_lap)
            if mean_interval > 0:
                variance = sum((x - mean_interval) ** 2 for x in self._step_intervals_this_lap) / len(self._step_intervals_this_lap)
                cv = math.sqrt(variance) / mean_interval  # coefficient of variation
                # Real walking cadence is fairly regular (cv roughly 0.1-0.4). Penalize wildly
                # irregular step timing, which is more consistent with noise than footsteps.
                step_score = max(0.0, 1.0 - max(0.0, cv - 0.4))
                score *= step_score
        else:
            score *= 0.6  # too few steps recorded for this lap to be confident

        if len(self._heading_deltas_this_lap) >= 5:
            max_single_jump = max(abs(d) for d in self._heading_deltas_this_lap)
            # A single tick contributing a large fraction of the full 360 suggests a glitch
            # (or the phone being spun by hand) rather than a walked lap.
            if max_single_jump > 60:
                score *= 0.5

        return round(max(0.0, min(1.0, score)), 2)

    def _reset_tracking_state(self):
        self.walking = False
        self.cumulative_heading = 0.0
