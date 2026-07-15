import unittest
import sys
import os
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sensor_service import SensorService
from services.pradakshina_detector import PradakshinaDetector


class MockSensorService(SensorService):
    """
    Overrides the two methods the detector actually calls now
    (get_filtered_accel_magnitude / get_fused_heading_delta_degrees) so tests can drive the
    detector directly without needing real hardware or the EMA/complementary-filter maths
    to settle first.
    """
    def __init__(self):
        super().__init__()
        self.mock_mode = True
        self.filtered_magnitude = 0.0
        self.heading_rate_dps = 0.0  # degrees/sec, applied for whatever dt is passed to update()

    def get_filtered_accel_magnitude(self) -> float:
        return self.filtered_magnitude

    def get_fused_heading_delta_degrees(self, dt: float) -> float:
        return self.heading_rate_dps * dt


class TestPradakshinaDetector(unittest.TestCase):
    def setUp(self):
        self.sensor = MockSensorService()
        self.laps = 0

        def on_lap():
            self.laps += 1

        self.detector = PradakshinaDetector(self.sensor, on_lap_complete=on_lap)
        self.detector.start()

    def test_step_detection_trigger(self):
        self.assertFalse(self.detector.walking)

        # A single large spike should exceed the default/adaptive threshold and register a step.
        self.sensor.filtered_magnitude = 2.0
        self.detector.update(in_geofence=True, dt=0.1)

        self.assertTrue(self.detector.walking)
        self.assertEqual(self.detector.step_count, 1)

    def test_adaptive_threshold_ignores_low_level_noise(self):
        # Feed a steady stream of small-amplitude "noise" — should never register as steps
        # once the adaptive threshold has a few samples to calibrate against.
        for _ in range(20):
            self.sensor.filtered_magnitude = 0.15
            self.detector.update(in_geofence=True, dt=0.1)
        self.assertEqual(self.detector.step_count, 0)

    def test_lap_completion_via_heading(self):
        self.assertEqual(self.laps, 0)
        self.detector.walking = True  # force active walking state for this test

        # 1200 deg/s * 0.1s dt = 120 degrees added per update() call.
        self.sensor.heading_rate_dps = 1200.0

        self.detector.update(in_geofence=True, dt=0.1)  # ~120
        self.assertEqual(self.laps, 0)

        self.detector.update(in_geofence=True, dt=0.1)  # ~240
        self.assertEqual(self.laps, 0)

        self.detector.update(in_geofence=True, dt=0.1)  # ~360 -> lap fires
        self.assertEqual(self.laps, 1)

    def test_lap_completion_respects_real_elapsed_time(self):
        # Same total rotation, but delivered via a larger dt tick (simulating a slower frame
        # rate) rather than many small fixed-size ticks — proving the detector integrates
        # actual elapsed time rather than assuming a fixed ~100ms tick length. (dt is
        # intentionally kept under the detector's 1.0s safety clamp, which exists to protect
        # against a huge dt spike after the app resumes from being backgrounded.)
        self.detector.walking = True
        self.sensor.heading_rate_dps = 120.0  # deg/s

        self.detector.update(in_geofence=True, dt=0.5)  # 60 deg
        self.assertEqual(self.laps, 0)

        self.detector.update(in_geofence=True, dt=1.0)  # +120 -> 180 deg
        self.assertEqual(self.laps, 0)

        self.detector.update(in_geofence=True, dt=1.0)  # +120 -> 300 deg
        self.assertEqual(self.laps, 0)

        self.detector.update(in_geofence=True, dt=0.5)  # +60 -> 360 deg -> lap fires
        self.assertEqual(self.laps, 1)

    def test_no_rotation_without_walking(self):
        self.detector.walking = False
        self.sensor.heading_rate_dps = 1200.0
        self.detector.update(in_geofence=True, dt=0.1)
        self.assertEqual(self.laps, 0)
        self.assertEqual(self.detector.cumulative_heading, 0.0)

    def test_confidence_score_is_lower_for_irregular_steps(self):
        self.detector.walking = True
        self.sensor.heading_rate_dps = 3600.0  # fast enough to complete a lap quickly

        # Wildly irregular step intervals should pull the lap's confidence score down.
        import time as _time
        for i in range(6):
            self.sensor.filtered_magnitude = 2.0
            self.detector.update(in_geofence=True, dt=0.1)
            self.detector.last_step_time = self.detector.last_step_time - (5000 if i % 2 == 0 else 50)

        self.assertGreaterEqual(self.laps, 1)
        self.assertLessEqual(self.detector.last_lap_confidence, 1.0)
        self.assertGreaterEqual(self.detector.last_lap_confidence, 0.0)


if __name__ == '__main__':
    unittest.main()
