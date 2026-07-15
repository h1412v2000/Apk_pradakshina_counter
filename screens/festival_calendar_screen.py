from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from plyer import notification

from theme import COLORS, GradientBackground, GlassCard, RoundButton, GhostButton, HeadingLabel, SubLabel


class FestivalCalendarScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=20, spacing=12)

        header = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=8)
        back_btn = GhostButton(text="\u2190 Home", size_hint_x=0.3, font_size='13sp')
        back_btn.bind(on_release=self.go_home)
        title = HeadingLabel(text="Festival Calendar", font_size='19sp')
        header.add_widget(back_btn)
        header.add_widget(title)
        layout.add_widget(header)

        scroll = ScrollView(size_hint_y=0.91)
        list_layout = GridLayout(cols=1, spacing=14, size_hint_y=None, padding=[0, 4, 0, 4])
        list_layout.bind(minimum_height=list_layout.setter('height'))

        festivals = [
            ("Guru Purnima", "2026-07-29", "Honor spiritual gurus \u2014 walk 108 pradakshinas."),
            ("Krishna Janmashtami", "2026-09-04", "Celebrating the birth of Lord Krishna."),
            ("Ganesh Chaturthi", "2026-09-16", "Vinayaka Chaturthi temple visits."),
            ("Navaratri Begins", "2026-10-12", "Nine days of spiritual focus and Devi pradakshinas."),
            ("Diwali / Deepavali", "2026-11-08", "Festival of Lights \u2014 special prayers at temples."),
        ]

        for name, date, desc in festivals:
            card = GlassCard(orientation='vertical', size_hint_y=None, height=118, padding=14, spacing=6)

            lbl_title = Label(text=f"{name}   \u00b7   {date}", font_size='15sp', bold=True,
                               color=COLORS["gold_bright"], halign='left')
            lbl_title.bind(size=lambda i, v: setattr(i, 'text_size', v))

            lbl_desc = SubLabel(text=desc, font_size='12sp', halign='left')
            lbl_desc.bind(size=lambda i, v: setattr(i, 'text_size', v))

            remind_btn = RoundButton(text="\U0001F514 Set Reminder", size_hint_y=None, height=36,
                                      font_size='12sp', fill_color=COLORS["maroon"])
            remind_btn.bind(on_release=lambda inst, n=name: self.set_reminder(n))

            card.add_widget(lbl_title)
            card.add_widget(lbl_desc)
            card.add_widget(remind_btn)
            list_layout.add_widget(card)

        scroll.add_widget(list_layout)
        layout.add_widget(scroll)
        root.add_widget(layout)
        self.add_widget(root)

    def set_reminder(self, name):
        title = "Temple Vow Reminder"
        message = f"Prepare for {name}! Don't forget to track your sacred vows."
        try:
            notification.notify(title=title, message=message)
        except Exception:
            print(f"Notification triggered locally: {title} - {message}")

    def go_home(self, instance):
        self.manager.current = 'home'
