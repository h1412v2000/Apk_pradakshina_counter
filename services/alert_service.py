from kivy.core.audio import SoundLoader
import time
from kivy.clock import Clock
import sys

try:
    from plyer import vibrator
except ImportError:
    vibrator = None


class AlertService:
    def __init__(self, sound_path="assets/sounds/target_reached.wav"):
        self.sound_path = sound_path
        self.sound = None
        self.sound_enabled = True
        self.vibration_enabled = True
        self._load_sound()

    def _load_sound(self):
        try:
            self.sound = SoundLoader.load(self.sound_path)
            if not self.sound:
                print("Warning: Could not load target_reached.wav")
        except Exception as e:
            print(f"Sound load error: {e}")

    def trigger_target_reached(self, target_count: int, on_screen_callback=None):
        print(f"🎯 Target Reached Alert: {target_count} laps completed!")

        # 1. Play Sound (with fallback)
        if self.sound_enabled:
            if self.sound:
                try:
                    self.sound.play()
                    # Loop sound for stronger effect
                    Clock.schedule_once(lambda dt: self._loop_sound_if_needed(), 2.5)
                except Exception as e:
                    print(f"Sound play error: {e}")
            else:
                # PC fallback beep
                try:
                    import winsound
                    for _ in range(3):
                        winsound.Beep(880, 600)
                        time.sleep(0.4)
                except Exception:
                    pass

        # 2. Strong Vibration Pattern
        if self.vibration_enabled and vibrator:
            try:
                # Pattern: strong vibration bursts
                vibrator.vibrate(0.6)
                Clock.schedule_once(lambda dt: vibrator.vibrate(0.8) if vibrator else None, 1.0)
                Clock.schedule_once(lambda dt: vibrator.vibrate(0.6) if vibrator else None, 2.2)
            except Exception as e:
                print(f"Vibration error: {e}")

        # 3. Call UI callback (popup)
        if on_screen_callback:
            on_screen_callback(target_count)

    def _loop_sound_if_needed(self):
        """Optional: replay sound once for emphasis"""
        if self.sound and self.sound_enabled:
            try:
                self.sound.play()
            except:
                pass