from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from theme import COLORS, GradientBackground, GlassCard, GhostButton, HeadingLabel, SubLabel


class TempleProfileScreen(Screen):
    def __init__(self, db_service, sensor_service, geofence_service, **kwargs):
        super().__init__(**kwargs)
        self.db = db_service
        self.sensor = sensor_service
        self.geofence = geofence_service

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        header = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=8)
        back_btn = GhostButton(text="\u2190 Back", size_hint_x=0.3, font_size='13sp')
        back_btn.bind(on_release=self.go_back)
        title = HeadingLabel(text="Temples Near You", font_size='18sp')
        header.add_widget(back_btn)
        header.add_widget(title)
        layout.add_widget(header)

        self.status_lbl = SubLabel(text="Locating\u2026", font_size='12sp', size_hint_y=0.06)
        layout.add_widget(self.status_lbl)

        scroll = ScrollView(size_hint_y=0.85)
        self.list_layout = GridLayout(cols=1, spacing=14, size_hint_y=None, padding=[0, 4, 0, 4])
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)

        layout.add_widget(scroll)
        root.add_widget(layout)
        self.add_widget(root)

    def on_enter(self):
        self.list_layout.clear_widgets()
        temples = self.db.get_all_temples()
        visits = self.db.get_recent_visits(limit=30)

        lat, lng = self.sensor.get_current_location(force_fresh=True)

        if lat is None or lng is None:
            self.status_lbl.text = "\u26A0 Waiting for a live GPS fix \u2014 showing all registered temples, unsorted."
            ordered = [(t, None) for t in temples]
        else:
            accuracy = self.sensor.get_location_accuracy_m()
            acc_txt = f" (\u00b1{int(accuracy)}m)" if accuracy else ""
            self.status_lbl.text = f"\U0001F4CD Sorted by live distance from your current location{acc_txt}"
            ordered = self.geofence.sorted_by_distance(lat, lng, temples)

        for temple, dist in ordered:
            card = GlassCard(orientation='vertical', size_hint_y=None, height=150, padding=14, spacing=4)

            total_laps = 0
            for v in visits:
                if v['temple_name'] == temple.name:
                    with self.db._get_connection() as conn:
                        row = conn.execute(
                            "SELECT SUM(count) FROM pradakshina_sessions WHERE visit_id = ?", (v['id'],)
                        ).fetchone()
                        if row and row[0]:
                            total_laps += row[0]

            name_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=24)
            name_lbl = Label(text=temple.name, font_size='16sp', bold=True,
                              color=COLORS["text_primary"], halign='left', valign='middle')
            name_lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
            name_row.add_widget(name_lbl)

            if dist is not None:
                within = dist <= temple.geofence_radius_m
                dist_text = "Here now" if within else (
                    f"{dist/1000:.1f} km" if dist >= 1000 else f"{int(dist)} m"
                )
                dist_lbl = Label(text=dist_text, font_size='12sp', bold=True,
                                  color=COLORS["success"] if within else COLORS["saffron"],
                                  size_hint_x=0.35, halign='right', valign='middle')
                dist_lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
                name_row.add_widget(dist_lbl)

            deity_lbl = SubLabel(text=f"{temple.deity}  \u2022  {temple.city}, {temple.state}", font_size='12sp')

            stats_lbl = Label(text=f"\U0001F6D5 {total_laps} pradakshinas completed", font_size='13sp',
                               bold=True, color=COLORS["gold_bright"], halign='left')
            stats_lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))

            card.add_widget(name_row)
            card.add_widget(deity_lbl)
            card.add_widget(stats_lbl)
            self.list_layout.add_widget(card)

    def go_back(self, instance):
        self.manager.current = 'home'
