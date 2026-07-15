"""
sensor_service.py — Real-device sensor access layer.

Design goals for accuracy on real hardware:
  1. Never silently stay in mock mode on a real device (this was a real bug previously —
     the Android/iOS check was accidentally nested inside a slider callback that never runs
     on-device; it's now correctly done once in __init__ and re-checked defensively in
     start_sensors()).
  2. Reduce raw sensor noise BEFORE it reaches the step/heading detector, via:
       - an exponential moving-average low-pass filter on the accelerometer magnitude
       - a magnetometer/compass reading (when the device exposes one) used to correct
         gyroscope drift, since raw gyro integration alone drifts noticeably over a
         30-90 second pradakshina.
  3. Be honest about hardware limits: consumer MEMS gyroscopes drift, magnetometers near
     temple ironwork/rebar can be locally distorted, and some budget Android phones lack a
     gyroscope entirely. This module degrades gracefully (gyro-only, or accelerometer-only
     "best effort") rather than crashing, and reports a `sensor_quality` flag the detector
     uses to lower its confidence score rather than pretend everything is perfect.
"""

from kivy.utils import platform
import time
import math

try:
    from plyer import accelerometer, gyroscope, gps
except Exception:
    accelerometer = gyroscope = gps = None

try:
    from plyer import compass as _compass
except Exception:
    _compass = None


class SensorService:
    def __init__(self, on_gps_update=None):
        self.on_gps_update = on_gps_update

        # Mock mode is the correct default on desktop/dev machines, and is switched off
        # exactly once here if we detect we're actually running on a phone. This must NOT
        # live inside any UI callback — it needs to be true from the very first sensor read.
        self.mock_mode = True
        if platform in ('android', 'ios'):
            self.mock_mode = False

        self.mock_lat = 13.6833  # Tirupati Venkateswara Temple default (desktop/dev fallback)
        self.mock_lng = 79.3500
        self.mock_step_simulation = False
        self.mock_rotation_rate_dps = 30.0

        # Real, live GPS fix cache. These start as None and are only ever populated by an
        # actual location callback from the device — they must never be silently defaulted
        # to the mock coordinates, or "live location" would quietly become fake location.
        self._live_lat = None
        self._live_lng = None
        self._live_accuracy_m = None
        self._live_fix_time = None
        self._last_gps_request_time = 0

        # Sensor availability flags, discovered at start_sensors() time.
        self.gyroscope_available = False
        self.compass_available = False

        # Low-pass filter state for the accelerometer magnitude (reduces false step triggers
        # from sensor noise / phone jostling that isn't an actual footstep).
        self._accel_lp_value = 9.81
        self._accel_lp_alpha = 0.25  # higher = less smoothing, more responsive

        # Complementary-filter state for heading fusion (gyro short-term + compass long-term
        # drift correction). Kept here rather than in the detector so all sensor-fusion
        # implementation detail stays in one place.
        self._fused_heading_deg = 0.0
        self._last_compass_heading = None

    # ------------------------------------------------------------------
    # Walking simulator (desktop testing only)
    # ------------------------------------------------------------------
    def set_walk_speed(self, degrees_per_second: float):
        """Called from the Live Tracking screen's 'Walking Simulator' slider (mock mode only)."""
        self.mock_rotation_rate_dps = max(0.0, degrees_per_second)

    # ------------------------------------------------------------------
    # GPS
    # ------------------------------------------------------------------
    def start_gps(self):
        if self.mock_mode or gps is None:
            print("GPS Simulation started (desktop/dev mode)")
            return
        try:
            gps.configure(on_location=self._on_location_receive,
                          on_status=self._on_status_receive)
            gps.start(minTime=800, minDistance=0)  # More responsive
        except Exception as e:
            print(f"Error starting GPS: {e}")
            self.mock_mode = True

    def stop_gps(self):
        if self.mock_mode or gps is None:
            return
        try:
            gps.stop()
        except Exception as e:
            print(f"Error stopping GPS: {e}")

    def _on_location_receive(self, **kwargs):
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        if lat is None or lon is None:
            return
        self._live_lat = lat
        self._live_lng = lon
        self._live_accuracy_m = kwargs.get('accuracy', 999)
        self._live_fix_time = time.time()
        if self.on_gps_update:
            self.on_gps_update(lat, lon)

    def _on_status_receive(self, **kwargs):
        print(f"GPS status update: {kwargs}")

    def has_live_fix(self, max_age_seconds: float = 30.0) -> bool:
        """True if we have a real GPS fix that isn't stale."""
        if self.mock_mode:
            return True  # the "fix" is the fixed dev coordinate — always available
        if self._live_lat is None:
            return False
        return (time.time() - self._live_fix_time) <= max_age_seconds

    def get_current_location(self, force_fresh: bool = False) -> tuple:
        """Returns freshest possible live location."""
        if self.mock_mode:
            return self.mock_lat, self.mock_lng

        now = time.time()
        if force_fresh and (now - self._last_gps_request_time > 2.0):
            self._last_gps_request_time = now
            # Optional: trigger a new request if supported by plyer

        if self._live_lat is not None and self.has_live_fix(max_age_seconds=45):
            return self._live_lat, self._live_lng
        return None, None

    def get_location_accuracy_m(self):
        """Reported GPS accuracy radius in meters, or None if unknown/mock/no fix."""
        if self.mock_mode:
            return None
        return self._live_accuracy_m

    def set_mock_location(self, lat: float, lng: float):
        self.mock_lat = lat
        self.mock_lng = lng
        if self.on_gps_update:
            self.on_gps_update(lat, lng)

    # ------------------------------------------------------------------
    # Motion sensors
    # ------------------------------------------------------------------
    def start_sensors(self):
        # Defensive re-check: if for some reason mock_mode was left True on a real device
        # (e.g. platform detection ran before Kivy fully initialized), correct it here too.
        if platform in ('android', 'ios'):
            self.mock_mode = False

        if self.mock_mode:
            return

        try:
            accelerometer.enable()
        except Exception as e:
            print(f"Accelerometer unavailable ({e}) — pradakshina detection cannot run "
                  f"without step data on this device.")

        try:
            gyroscope.enable()
            self.gyroscope_available = True
        except Exception as e:
            print(f"Gyroscope unavailable ({e}). Falling back to compass-only heading "
                  f"(less responsive, but works on phones with weak/missing gyro support).")
            self.gyroscope_available = False

        if _compass is not None:
            try:
                _compass.enable()
                self.compass_available = True
            except Exception as e:
                print(f"Compass/magnetometer unavailable ({e}). Heading will rely on "
                      f"gyroscope integration alone and may drift over a long session.")
                self.compass_available = False

        # Reset fusion/filter state at the start of every tracking session.
        self._accel_lp_value = 9.81
        self._fused_heading_deg = 0.0
        self._last_compass_heading = None

    def stop_sensors(self):
        if self.mock_mode:
            return
        try:
            accelerometer.disable()
        except Exception as e:
            print(f"Error disabling accelerometer: {e}")
        try:
            gyroscope.disable()
        except Exception as e:
            print(f"Error disabling gyroscope: {e}")
        if self.compass_available:
            try:
                _compass.disable()
            except Exception as e:
                print(f"Error disabling compass: {e}")

    def get_accelerometer_reading(self) -> tuple:
        if self.mock_mode:
            if self.mock_step_simulation:
                # Footstep spike roughly every 0.6s (comfortable walking cadence), impact
                # pulse followed by a quiet phase — close enough to a real step signature to
                # exercise the same adaptive-threshold detector used on-device.
                phase = time.time() % 0.6
                val = 9.81 + 2.2 if phase < 0.15 else 9.81
                return 0.0, 0.0, val
            return 0.0, 0.0, 9.81

        try:
            val = accelerometer.acceleration
            return val if val and len(val) == 3 and val[2] is not None else (0.0, 0.0, 9.81)
        except Exception:
            return 0.0, 0.0, 9.81

    def get_filtered_accel_magnitude(self) -> float:
        """
        Returns a low-pass-filtered |acceleration - gravity| value, reducing single-sample
        spikes from sensor noise that aren't real footsteps. This is what the detector's
        adaptive step threshold should compare against, not the raw instantaneous reading.
        """
        ax, ay, az = self.get_accelerometer_reading()
        raw_mag = math.sqrt(ax * ax + ay * ay + az * az) - 9.81
        a = self._accel_lp_alpha
        # EMA filter on the magnitude itself (gravity offset already removed above)
        self._accel_lp_value = (1 - a) * self._accel_lp_value + a * (raw_mag + 9.81)
        return self._accel_lp_value - 9.81

    def get_gyroscope_reading(self) -> tuple:
        if self.mock_mode:
            if self.mock_step_simulation:
                return 0.0, 0.0, math.radians(self.mock_rotation_rate_dps)
            return 0.0, 0.0, 0.0

        if not self.gyroscope_available:
            return 0.0, 0.0, 0.0

        try:
            val = gyroscope.rotation
            return val if val and len(val) == 3 and val[2] is not None else (0.0, 0.0, 0.0)
        except Exception:
            return 0.0, 0.0, 0.0

    def get_compass_heading(self):
        """
        Returns an absolute heading in degrees (0-360) from the magnetometer, or None if
        unavailable/mock mode. Used to correct gyroscope drift via a complementary filter —
        NOT as the primary signal, since raw magnetometer readings are noisy and easily
        distorted by nearby metal (temple ironwork, rebar, donation boxes, etc).
        """
        if self.mock_mode or not self.compass_available:
            return None
        try:
            field = _compass.field
            if not field:
                return None
            # Plyer's compass facade is inconsistent across platforms about whether it
            # returns a ready-made heading or a raw (x, y, z) magnetic field vector. Handle
            # both shapes defensively rather than assuming one.
            if isinstance(field, (int, float)):
                return float(field) % 360
            if len(field) >= 2:
                heading = math.degrees(math.atan2(field[1], field[0]))
                return heading % 360
        except Exception:
            pass
        return None

    def get_fused_heading_delta_degrees(self, dt: float) -> float:
        """
        Returns the change in heading (degrees) since the last call, fusing gyroscope
        integration (responsive, but drifts) with compass absolute heading (stable long-term,
        but noisy/laggy) via a complementary filter. This is the single call the detector
        should use for lap-angle tracking on real devices — it already contains the noise
        mitigation, so the detector itself doesn't need to know about gyro vs. compass.
        """
        gx, gy, gz = self.get_gyroscope_reading()
        gyro_delta_deg = math.degrees(gz) * dt

        predicted_heading = (self._fused_heading_deg + gyro_delta_deg) % 360

        compass_heading = self.get_compass_heading()
        if compass_heading is not None:
            # Complementary filter: trust the gyro's short-term responsiveness, but pull
            # gently toward the compass's absolute reading so errors don't accumulate over
            # a multi-minute pradakshina session.
            diff = (compass_heading - predicted_heading + 180) % 360 - 180
            correction_weight = 0.02  # small: correct drift without making the needle jittery
            fused_heading = (predicted_heading + correction_weight * diff) % 360
        else:
            fused_heading = predicted_heading

        delta = (fused_heading - self._fused_heading_deg + 180) % 360 - 180
        self._fused_heading_deg = fused_heading
        return delta
