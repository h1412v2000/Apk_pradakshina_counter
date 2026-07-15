from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from datetime import datetime, timedelta

from theme import COLORS, GradientBackground, GlassCard, RoundButton, GhostButton, HeadingLabel, SubLabel


class SankalpaScreen(Screen):
    def __init__(self, db_service, **kwargs):
        super().__init__(**kwargs)
        self.db = db_service

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=20, spacing=12)

        header = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=8)
        back_btn = GhostButton(text="\u2190 Home", size_hint_x=0.3, font_size='13sp')
        back_btn.bind(on_release=self.go_home)
        title = HeadingLabel(text="My Vows (Sankalpa)", font_size='18sp')
        header.add_widget(back_btn)
        header.add_widget(title)
        layout.add_widget(header)

        new_vow_btn = RoundButton(text="+ Make a New Vow", size_hint_y=0.1, font_size='15sp',
                                   bold=True, fill_color=COLORS["saffron"])
        new_vow_btn.bind(on_release=self.show_new_vow_popup)
        layout.add_widget(new_vow_btn)

        scroll = ScrollView(size_hint_y=0.81)
        self.list_layout = GridLayout(cols=1, spacing=14, size_hint_y=None, padding=[0, 4, 0, 4])
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)

        root.add_widget(layout)
        self.add_widget(root)

    def on_enter(self):
        self.refresh_sankalpas()

    def refresh_sankalpas(self):
        self.list_layout.clear_widgets()
        sankalpas = self.db.get_active_sankalpas()

        if not sankalpas:
            self.list_layout.add_widget(
                SubLabel(text="No active vows yet. Start a new Sankalpa above.",
                         size_hint_y=None, height=50)
            )
            return

        for s in sankalpas:
            card = GlassCard(orientation='vertical', size_hint_y=None, height=138, padding=14, spacing=6)

            hdr = Label(text=s.description, font_size='16sp', bold=True,
                        color=COLORS["text_primary"], halign='left')
            hdr.bind(size=lambda i, v: setattr(i, 'text_size', v))

            status_text = f"{s.current_progress}/{s.target_count} {s.target_type}  \u2022  {s.status.upper()}"
            sub = SubLabel(text=status_text, font_size='12sp', halign='left')
            sub.bind(size=lambda i, v: setattr(i, 'text_size', v))

            progress = ProgressBar(max=s.target_count, value=min(s.current_progress, s.target_count),
                                    size_hint_y=None, height=8)

            deadline_lbl = Label(text=f"Deadline: {s.deadline_date}", font_size='11sp',
                                  color=COLORS["saffron"], halign='left')
            deadline_lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))

            card.add_widget(hdr)
            card.add_widget(sub)
            card.add_widget(progress)
            card.add_widget(deadline_lbl)
            self.list_layout.add_widget(card)

    def show_new_vow_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=18, spacing=10)

        content.add_widget(Label(text="Vow / Resolution Description:", font_size='14sp',
                                  bold=True, color=COLORS["text_primary"], size_hint_y=None, height=24))
        desc_input = TextInput(text="Walk 108 Laps", multiline=False, size_hint_y=None, height=40)
        content.add_widget(desc_input)

        content.add_widget(Label(text="Target Count (e.g. 108):", font_size='14sp',
                                  bold=True, color=COLORS["text_primary"], size_hint_y=None, height=24))
        count_input = TextInput(text="108", multiline=False, size_hint_y=None, height=40)
        content.add_widget(count_input)

        content.add_widget(Label(text="Type (pradakshina / japa):", font_size='14sp',
                                  bold=True, color=COLORS["text_primary"], size_hint_y=None, height=24))
        type_input = TextInput(text="pradakshina", multiline=False, size_hint_y=None, height=40)
        content.add_widget(type_input)

        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=55, spacing=10)
        save_btn = RoundButton(text="Save Vow", fill_color=COLORS["saffron"])
        cancel_btn = GhostButton(text="Cancel")
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        content.add_widget(btn_box)

        popup = Popup(title="Take a New Vow (Sankalpa)", content=content, size_hint=(0.9, 0.75),
                       background_color=COLORS["bg_bottom"])

        def save_vow(inst):
            try:
                desc = desc_input.text.strip()
                target = int(count_input.text.strip())
                vtype = type_input.text.strip().lower()
                if vtype not in ['pradakshina', 'japa']:
                    vtype = 'pradakshina'
                deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

                self.db.create_sankalpa(1, desc, target, vtype, deadline)
                popup.dismiss()
                self.refresh_sankalpas()
            except ValueError:
                pass

        save_btn.bind(on_release=save_vow)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def go_home(self, instance):
        self.manager.current = 'home'
