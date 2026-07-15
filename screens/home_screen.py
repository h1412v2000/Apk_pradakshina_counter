from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock

from theme import (COLORS, GradientBackground, GlassCard, RoundButton,
                    GhostButton, HeadingLabel, SubLabel, BigStatLabel)


class HomeScreen(Screen):
    nearest_temple_name = StringProperty("Scanning for nearby temple...")
    streak_count = NumericProperty(0)
    today_laps = NumericProperty(0)

    def __init__(self, db_service, sensor_service, geofence_service, **kwargs):
        super().__init__(**kwargs)
        self.db = db_service
        self.sensor = sensor_service
        self.geofence = geofence_service

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=24, spacing=16)

        # Header
        header = BoxLayout(orientation='vertical', size_hint_y=0.18, spacing=2)
        header.add_widget(HeadingLabel(text="\U0001F6D5 Pradakshina Tracker", font_size='26sp', halign='left'))
        header.add_widget(SubLabel(text="Your Sacred Journey Companion", halign='left'))
        layout.add_widget(header)

        # Streak + Today stat cards, side by side
        stats_row = BoxLayout(orientation='horizontal', size_hint_y=0.24, spacing=14)

        streak_card = GlassCard(orientation='vertical', padding=14, spacing=4)
        streak_card.add_widget(SubLabel(text="DAILY STREAK", font_size='11sp', bold=True))
        self.streak_lbl = BigStatLabel(text="0", font_size='34sp')
        streak_card.add_widget(self.streak_lbl)
        streak_card.add_widget(SubLabel(text="days", font_size='12sp'))
        stats_row.add_widget(streak_card)

        today_card = GlassCard(orientation='vertical', padding=14, spacing=4)
        today_card.add_widget(SubLabel(text="TODAY", font_size='11sp', bold=True))
        self.today_lbl = BigStatLabel(text="0", font_size='34sp', color=COLORS["saffron"])
        today_card.add_widget(self.today_lbl)
        today_card.add_widget(SubLabel(text="pradakshinas", font_size='12sp'))
        stats_row.add_widget(today_card)

        layout.add_widget(stats_row)

        # Geofence status card
        geofence_card = GlassCard(orientation='vertical', size_hint_y=0.2, padding=16, spacing=6)
        geofence_card.add_widget(SubLabel(text="\U0001F4CD NEAREST TEMPLE", font_size='11sp', bold=True))
        self.geo_name = Label(
            text=self.nearest_temple_name,
            font_size='17sp',
            bold=True,
            halign='center',
            valign='middle',
            color=COLORS["text_primary"],
        )
        self.geo_name.bind(size=lambda i, v: setattr(i, 'text_size', v))
        geofence_card.add_widget(self.geo_name)
        layout.add_widget(geofence_card)

        # Start Tracking — primary CTA
        start_btn = RoundButton(
            text="\u2726  Start Tracking",
            size_hint_y=0.14,
            font_size='19sp',
            bold=True,
            fill_color=COLORS["saffron"],
        )
        start_btn.bind(on_release=self.go_to_tracking)
        layout.add_widget(start_btn)

        # Nav grid
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=0.12, spacing=10)
        screens = [
            ("Sankalpa", "sankalpa"),
            ("Stats", "stats"),
            ("Calendar", "calendar"),
            ("Temples", "temples"),
        ]
        for name, screen_id in screens:
            btn = GhostButton(text=name, font_size='13sp')
            btn.bind(on_release=lambda x, sid=screen_id: self.navigate_to(sid))
            nav_bar.add_widget(btn)
        layout.add_widget(nav_bar)

        root.add_widget(layout)
        self.add_widget(root)

        Clock.schedule_interval(self.check_geofence, 3.0)

    def on_enter(self):
        streak = self.db.get_streak()
        if streak:
            self.streak_lbl.text = str(streak.current_count)

        visits = self.db.get_recent_visits(limit=10)
        today_laps_count = 0
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        for v in visits:
            if v['start_time'].startswith(today_str):
                with self.db._get_connection() as conn:
                    row = conn.execute(
                        "SELECT SUM(count) FROM pradakshina_sessions WHERE visit_id = ?", (v['id'],)
                    ).fetchone()
                    if row and row[0]:
                        today_laps_count += row[0]

        self.today_lbl.text = str(today_laps_count)
        self.check_geofence(0)

    def check_geofence(self, dt):
        lat, lng = self.sensor.get_current_location(force_fresh=True)
        temples = self.db.get_all_temples()

        if lat is None or lng is None:
            self.nearest_temple_name = "Waiting for GPS fix\u2026"
            self.geo_name.color = COLORS["text_muted"]
            self.geo_name.text = self.nearest_temple_name
            return

        nearest, dist = self.geofence.find_nearest_temple(lat, lng, temples)
        if nearest:
            if dist <= nearest.geofence_radius_m:
                self.nearest_temple_name = f"At {nearest.name}\n(within sacred grounds)"
                self.geo_name.color = COLORS["success"]
            else:
                self.nearest_temple_name = f"{nearest.name}\n~{int(dist)}m away"
                self.geo_name.color = COLORS["text_primary"]
        else:
            self.nearest_temple_name = "No registered temples nearby."
            self.geo_name.color = COLORS["text_muted"]
        self.geo_name.text = self.nearest_temple_name

    def go_to_tracking(self, instance):
        self.manager.current = 'set_target'

    def navigate_to(self, screen_id):
        self.manager.current = screen_id
