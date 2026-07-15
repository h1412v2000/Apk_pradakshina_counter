from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.clock import Clock

from services.pradakshina_detector import PradakshinaDetector
from widgets.rotating_compass_widget import RotatingCompassWidget
from services.alert_service import AlertService
from theme import (COLORS, GradientBackground, GlassCard, RoundButton,
                    GhostButton, HeadingLabel, SubLabel, BigStatLabel)


class LiveTrackingScreen(Screen):
    def __init__(self, db_service, sensor_service, geofence_service, **kwargs):
        super().__init__(**kwargs)
        self.db = db_service
        self.sensor = sensor_service
        self.geofence = geofence_service

        self.active_visit_id = None
        self.lap_count = 0
        self.target_count = 108
        self.target_reached_triggered = False
        self.session_active = False
        self.active_temple = None
        self.current_lat, self.current_lng = None, None
        self._active_temple_dist = float('inf')

        self.detector = PradakshinaDetector(
            self.sensor,
            on_lap_complete=self.on_lap_completed,
            on_step_detected=self.on_step_detected,
        )
        self.alert_service = AlertService()

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        self.main_layout = BoxLayout(orientation='vertical', padding=[20, 20, 20, 16], spacing=10)

        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=8)
        back_btn = GhostButton(text="\u2190 Home", size_hint_x=0.3, font_size='13sp')
        back_btn.bind(on_release=self.go_home)
        self.temple_lbl = Label(text="Sanctum Tracking", font_size='16sp', bold=True,
                                 color=COLORS["saffron"])
        header.add_widget(back_btn)
        header.add_widget(self.temple_lbl)
        self.main_layout.add_widget(header)

        # Rotating compass + progress ring centerpiece
        compass_wrap = BoxLayout(size_hint_y=0.36)
        self.compass_widget = RotatingCompassWidget()
        compass_wrap.add_widget(self.compass_widget)
        self.main_layout.add_widget(compass_wrap)

        # Lap count, large and bold
        self.lap_lbl = BigStatLabel(text="0 / 108", font_size='30sp', size_hint_y=0.1)
        self.main_layout.add_widget(self.lap_lbl)

        self.status_lbl = SubLabel(text="Steps: 0  \u2022  Heading: 0\u00b0", font_size='12sp', size_hint_y=0.05)
        self.main_layout.add_widget(self.status_lbl)

        # Manual correction controls
        manual_box = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=10)
        minus_btn = RoundButton(text="\u2212 1 Lap", font_size='15sp', fill_color=COLORS["maroon"])
        minus_btn.bind(on_release=self.decrement_lap)
        plus_btn = RoundButton(text="+ 1 Lap", font_size='15sp', fill_color=COLORS["success"])
        plus_btn.bind(on_release=self.increment_lap)
        manual_box.add_widget(minus_btn)
        manual_box.add_widget(plus_btn)
        self.main_layout.add_widget(manual_box)

        # Session controls
        controls = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=12)
        self.start_pause_btn = RoundButton(text="Start Session", font_size='15sp', bold=True,
                                            fill_color=COLORS["saffron"])
        self.start_pause_btn.bind(on_release=self.toggle_session)
        self.end_btn = GhostButton(text="End & Save", font_size='15sp')
        self.end_btn.bind(on_release=self.end_session)
        controls.add_widget(self.start_pause_btn)
        controls.add_widget(self.end_btn)
        self.main_layout.add_widget(controls)

        # Simulation panel (desktop/testing only — hidden automatically on real devices).
        # This simulates an actual devotee walking a circumambulation: toggling "Start
        # Walking" begins continuous footsteps + continuous heading rotation at the chosen
        # speed, exactly like a real accelerometer+gyroscope would report while circling the
        # sanctum. It is NOT a "jump to this angle" control — the heading climbs smoothly
        # from wherever it currently is, and a lap fires automatically at 360°.
        self.simulation_panel = GlassCard(orientation='vertical', size_hint_y=0.25, padding=12, spacing=6)
        self.simulation_panel.add_widget(
            SubLabel(text="\u2699 DESKTOP WALKING SIMULATOR", font_size='10sp', bold=True, size_hint_y=0.2)
        )
        sim_grid = GridLayout(cols=2, spacing=6, size_hint_y=0.6)
        sim_grid.add_widget(SubLabel(text="Start Walking", font_size='12sp'))
        self.walk_switch = Switch(active=False)
        self.walk_switch.bind(active=self.toggle_mock_walk)
        sim_grid.add_widget(self.walk_switch)

        sim_grid.add_widget(SubLabel(text="Walking Speed", font_size='12sp'))
        self.rotation_slider = Slider(min=5, max=90, value=30)
        self.rotation_slider.bind(value=self.on_rotation_slider)
        sim_grid.add_widget(self.rotation_slider)

        self.simulation_panel.add_widget(sim_grid)
        self.sim_speed_lbl = SubLabel(text="30\u00b0/sec  \u2248  12s per lap", font_size='11sp', size_hint_y=0.2)
        self.simulation_panel.add_widget(self.sim_speed_lbl)
        self.main_layout.add_widget(self.simulation_panel)

        root.add_widget(self.main_layout)
        self.add_widget(root)

    def on_enter(self):
        self.resolve_active_temple(force_fresh=True)

        self.lap_count = 0
        self.target_reached_triggered = False
        self.session_active = False
        self.start_pause_btn.text = "Start Session"
        self.start_pause_btn.fill_color = COLORS["saffron"]
        self.detector.stop()
        self.walk_switch.active = False
        self.rotation_slider.value = 30
        self.sensor.set_walk_speed(30)
        self.sensor.mock_step_simulation = False
        self.compass_widget.heading = 0.0
        self.compass_widget.progress = 0.0
        self.detector.cumulative_heading = 0.0

        if not self.sensor.mock_mode:
            try:
                self.main_layout.remove_widget(self.simulation_panel)
            except Exception:
                pass

        self.update_ui_details()

    def resolve_active_temple(self, force_fresh: bool = True):
        """Always use the freshest GPS when starting a session."""
        lat, lng = self.sensor.get_current_location(force_fresh=force_fresh)
        temples = self.db.get_all_temples()

        if lat is None or lng is None:
            self.active_temple = None
            self.current_lat, self.current_lng = None, None
            self.temple_lbl.text = "Waiting for accurate GPS fix..."
            self.temple_lbl.color = COLORS["text_muted"]
            return

        self.current_lat, self.current_lng = lat, lng
        nearest, dist = self.geofence.find_nearest_temple(lat, lng, temples)
        self.active_temple = nearest
        self._active_temple_dist = dist

        if nearest and dist <= nearest.geofence_radius_m + 30:  # small tolerance
            self.temple_lbl.text = f"At {nearest.name}"
            self.temple_lbl.color = COLORS["success"]
        elif nearest:
            self.temple_lbl.text = f"{nearest.name} (~{int(dist)}m away)"
            self.temple_lbl.color = COLORS["saffron"]
        else:
            self.temple_lbl.text = "No registered temple nearby"
            self.temple_lbl.color = COLORS["text_muted"]

    def toggle_session(self, instance):
        if self.session_active:
            # Pause logic...
            self.session_active = False
            self.detector.stop()
            self.start_pause_btn.text = "Resume Session"
            self.start_pause_btn.fill_color = COLORS["success"]
            Clock.unschedule(self.update_tick)
        else:
            # === CRITICAL: Fresh location on every Start ===
            self.resolve_active_temple(force_fresh=True)

            self.session_active = True
            self.detector.start()
            self.start_pause_btn.text = "Pause Session"
            self.start_pause_btn.fill_color = COLORS["maroon"]

            if not self.active_visit_id and self.active_temple:
                self.active_visit_id = self.db.start_visit(1, self.active_temple.id, source='auto')
            elif not self.active_temple:
                # Allow tracking even without temple (for unknown locations)
                self.active_visit_id = self.db.start_visit(1, 1, source='manual')  # fallback

            Clock.schedule_interval(self.update_tick, 0.08)  # slightly faster update

    def update_tick(self, dt):
        lat, lng = self.sensor.get_current_location()
        in_geofence = True

        if not self.sensor.mock_mode and self.active_temple and lat and lng:
            in_geofence = self.geofence.is_inside_geofence(lat, lng, self.active_temple)

        self.detector.update(in_geofence=in_geofence, dt=dt)
        self.compass_widget.heading = self.detector.cumulative_heading % 360
        self.update_ui_details()

    def update_ui_details(self):
        heading = int(self.detector.cumulative_heading) % 360
        self.lap_lbl.text = f"{self.lap_count} / {self.target_count if self.target_count else '\u221e'}"
        conf_pct = int(self.detector.last_lap_confidence * 100)
        self.status_lbl.text = (
            f"Steps: {self.detector.step_count}  \u2022  Heading: {heading}\u00b0  "
            f"\u2022  Last lap confidence: {conf_pct}%"
        )
        if self.target_count and self.target_count > 0:
            self.compass_widget.progress = min(1.0, self.lap_count / self.target_count)
        else:
            self.compass_widget.progress = 0.0

    def on_lap_completed(self):
        self.lap_count += 1
        self.compass_widget.pulse()
        self.update_ui_details()
        self.check_target()

    def on_step_detected(self, steps):
        self.update_ui_details()

    def increment_lap(self, instance):
        self.lap_count += 1
        self.compass_widget.pulse()
        self.update_ui_details()
        self.check_target()

    def decrement_lap(self, instance):
        if self.lap_count > 0:
            self.lap_count -= 1
        self.update_ui_details()

    def trigger_target_reached_alert(self):
        """Strong, unmistakable alert when target is completed."""
        self.target_reached_triggered = True

        # Stop automatic tracking
        self.detector.stop()
        self.session_active = False
        Clock.unschedule(self.update_tick)

        # Update UI to show completion
        self.start_pause_btn.text = "Target Complete"
        self.start_pause_btn.fill_color = COLORS["success"]

        # Trigger Alarm + Vibration + Popup
        self.alert_service.trigger_target_reached(
            self.target_count,
            self.show_target_reached_popup
        )

        # Extra visual feedback
        self.compass_widget.pulse()  # golden flash

    def show_target_reached_popup(self, target_count):
        content = BoxLayout(orientation='vertical', padding=20, spacing=18)

        lbl = Label(
            text=f"\U0001F64F  Sankalpa Complete!\n\n{target_count} Pradakshinas Finished",
            font_size='19sp',
            halign='center',
            valign='middle',
            bold=True,
            color=COLORS["gold_bright"],
        )
        lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
        content.add_widget(lbl)

        buttons = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=0.4)
        cont_btn = RoundButton(text="Continue Tracking", fill_color=COLORS["success"])
        end_btn = RoundButton(text="End & Save Session", fill_color=COLORS["saffron"])

        buttons.add_widget(cont_btn)
        buttons.add_widget(end_btn)
        content.add_widget(buttons)

        popup = Popup(
            title="",
            separator_height=0,
            content=content,
            size_hint=(0.88, 0.42),
            auto_dismiss=False,
            background_color=COLORS["bg_bottom"],
        )

        def on_continue(inst):
            popup.dismiss()
            # Allow continuing beyond target
            self.target_reached_triggered = False
            self.target_count = 0  # unlimited mode
            self.toggle_session(None)

        def on_end(inst):
            popup.dismiss()
            self.end_session(None)

        cont_btn.bind(on_release=on_continue)
        end_btn.bind(on_release=on_end)
        popup.open()

    def check_target(self):
        """Check if target is reached and trigger alarm immediately."""
        if (self.target_count > 0 and 
            self.lap_count >= self.target_count and 
            not self.target_reached_triggered):
            
            self.target_reached_triggered = True
            self.trigger_target_reached_alert()

    def end_session(self, instance):
        Clock.unschedule(self.update_tick)
        self.detector.stop()

        if self.active_visit_id and self.lap_count > 0:
            reached_flag = 1 if self.lap_count >= self.target_count else 0
            confidences = self.detector.session_confidences
            avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.5
            self.db.add_pradakshina_session(
                self.active_visit_id,
                self.lap_count,
                confidence_score=avg_confidence,
                target_count=self.target_count,
                target_reached=reached_flag
            )
            self.db.end_visit(self.active_visit_id)

        self.active_visit_id = None
        self.go_home(None)

    def toggle_mock_walk(self, switch, value):
        self.sensor.mock_step_simulation = value

    def on_rotation_slider(self, slider, value):
        if self.sensor.mock_mode:
            self.sensor.set_walk_speed(value)
            lap_seconds = 360.0 / value if value > 0 else 0
            self.sim_speed_lbl.text = f"{value:.0f}\u00b0/sec  \u2248  {lap_seconds:.0f}s per lap"

    def go_home(self, instance):
        Clock.unschedule(self.update_tick)
        self.detector.stop()
        self.manager.current = 'home'
