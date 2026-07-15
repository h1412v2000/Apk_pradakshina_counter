from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle

from theme import COLORS, GradientBackground, GlassCard, GhostButton, HeadingLabel, SubLabel, BigStatLabel


class CustomBarChart(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.bind(pos=self.draw_chart, size=self.draw_chart)

    def set_data(self, data):
        self.data = data
        self.draw_chart()

    def draw_chart(self, *args):
        self.canvas.clear()
        if not self.data:
            return

        x_start = self.x + 20
        y_start = self.y + 40
        chart_width = self.width - 40
        chart_height = self.height - 80

        max_val = max([val for name, val in self.data]) if self.data else 1
        if max_val == 0:
            max_val = 1

        num_bars = len(self.data)
        bar_gap = 15
        total_gaps_w = bar_gap * (num_bars + 1)
        bar_width = (chart_width - total_gaps_w) / num_bars if num_bars > 0 else chart_width

        with self.canvas:
            Color(1, 1, 1, 0.12)
            RoundedRectangle(pos=(x_start, y_start - 5), size=(chart_width, 3), radius=[2])

            for i, (name, val) in enumerate(self.data):
                bar_x = x_start + bar_gap + i * (bar_width + bar_gap)
                bar_h = (val / max_val) * chart_height
                if bar_h < 5:
                    bar_h = 5

                Color(*COLORS["saffron"])
                RoundedRectangle(pos=(bar_x, y_start), size=(bar_width, bar_h), radius=[6, 6, 0, 0])


class LifetimeStatsScreen(Screen):
    def __init__(self, db_service, **kwargs):
        super().__init__(**kwargs)
        self.db = db_service

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=20, spacing=14)

        header = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=8)
        back_btn = GhostButton(text="\u2190 Home", size_hint_x=0.3, font_size='13sp')
        back_btn.bind(on_release=self.go_home)
        title = HeadingLabel(text="Lifetime Stats", font_size='19sp')
        header.add_widget(back_btn)
        header.add_widget(title)
        layout.add_widget(header)

        stats_card = GlassCard(orientation='vertical', size_hint_y=0.22, padding=16, spacing=4)
        stats_card.add_widget(SubLabel(text="LIFETIME PRADAKSHINAS", font_size='11sp', bold=True))
        self.total_lbl = BigStatLabel(text="0", font_size='36sp')
        stats_card.add_widget(self.total_lbl)
        self.japa_lbl = SubLabel(text="Total Japa: 0 counts", font_size='13sp')
        stats_card.add_widget(self.japa_lbl)
        layout.add_widget(stats_card)

        layout.add_widget(SubLabel(text="TEMPLE-WISE BREAKDOWN", font_size='12sp', bold=True, size_hint_y=0.05))

        chart_card = GlassCard(orientation='vertical', size_hint_y=0.46, padding=10)
        self.chart = CustomBarChart()
        chart_card.add_widget(self.chart)
        layout.add_widget(chart_card)

        self.legend_box = BoxLayout(orientation='vertical', size_hint_y=0.18, spacing=3)
        layout.add_widget(self.legend_box)

        root.add_widget(layout)
        self.add_widget(root)

    def on_enter(self):
        stats = self.db.get_lifetime_stats()
        self.total_lbl.text = str(stats['total_pradakshinas'])
        self.japa_lbl.text = f"Total Japa: {stats['total_japa']} counts"

        breakdown = stats['temple_breakdown']
        chart_data = []
        self.legend_box.clear_widgets()

        if breakdown:
            for item in breakdown[:5]:
                chart_data.append((item['name'], item['total']))
                lbl = Label(text=f"\u2022 {item['name']}: {item['total']} laps", font_size='12sp',
                            color=COLORS["text_muted"], halign='left')
                lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
                self.legend_box.add_widget(lbl)
            self.chart.set_data(chart_data)
        else:
            self.chart.set_data([("No Data", 0)])

    def go_home(self, instance):
        self.manager.current = 'home'
