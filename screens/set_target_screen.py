from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput

from theme import (COLORS, GradientBackground, GlassCard, RoundButton,
                    GhostButton, ChipButton, HeadingLabel, SubLabel)


class SetTargetScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = FloatLayout()
        root.add_widget(GradientBackground(size_hint=(1, 1)))

        layout = BoxLayout(orientation='vertical', padding=24, spacing=18)

        # Header
        header = BoxLayout(orientation='vertical', size_hint_y=0.16, spacing=4)
        header.add_widget(HeadingLabel(text="Set Your Sankalpa", font_size='25sp'))
        header.add_widget(SubLabel(text="Choose your pradakshina target for this session"))
        layout.add_widget(header)

        # Quick select chips
        chips_card = GlassCard(orientation='vertical', size_hint_y=0.42, padding=18, spacing=12)
        chips_card.add_widget(SubLabel(text="QUICK SELECT", font_size='11sp', bold=True))

        grid = GridLayout(cols=3, spacing=10, size_hint_y=0.75)
        self.chip_buttons = {}
        targets = [2, 11, 27, 54, 108]
        for t in targets:
            chip = ChipButton(text=str(t), font_size='18sp', bold=True)
            chip.bind(on_release=lambda inst, val=t: self.select_quick_target(val))
            self.chip_buttons[t] = chip
            grid.add_widget(chip)

        clear_chip = ChipButton(text="Custom", font_size='14sp', fill_color=(1, 1, 1, 0.05))
        clear_chip.bind(on_release=lambda inst: self.select_quick_target(0))
        self.chip_buttons[0] = clear_chip
        grid.add_widget(clear_chip)

        chips_card.add_widget(grid)
        layout.add_widget(chips_card)

        # Custom input
        custom_card = GlassCard(orientation='vertical', size_hint_y=0.18, padding=16, spacing=8)
        custom_card.add_widget(SubLabel(text="OR ENTER A CUSTOM NUMBER", font_size='11sp', bold=True))
        self.custom_input = TextInput(
            text="108",
            multiline=False,
            input_filter='int',
            font_size='22sp',
            halign='center',
            background_color=(0, 0, 0, 0),
            foreground_color=COLORS["gold_bright"],
            cursor_color=COLORS["saffron"],
            padding_y=[10, 10],
        )
        self.custom_input.bind(text=self._on_custom_text)
        custom_card.add_widget(self.custom_input)
        layout.add_widget(custom_card)

        # Actions
        actions = BoxLayout(orientation='horizontal', size_hint_y=0.14, spacing=15)
        cancel_btn = GhostButton(text="Cancel", font_size='17sp')
        cancel_btn.bind(on_release=self.go_back)
        start_btn = RoundButton(text="Begin \u2728", font_size='17sp', bold=True, fill_color=COLORS["saffron"])
        start_btn.bind(on_release=self.start_session)

        actions.add_widget(cancel_btn)
        actions.add_widget(start_btn)
        layout.add_widget(actions)

        root.add_widget(layout)
        self.add_widget(root)

        self._highlight_matching_chip()

    def _on_custom_text(self, instance, value):
        self._highlight_matching_chip()

    def _highlight_matching_chip(self):
        try:
            current = int(self.custom_input.text.strip())
        except ValueError:
            current = -1
        for t, chip in self.chip_buttons.items():
            chip.set_selected(t == current and t != 0)

    def select_quick_target(self, target_val):
        if target_val == 0:
            self.custom_input.text = ""
        else:
            self.custom_input.text = str(target_val)
        self._highlight_matching_chip()

    def go_back(self, instance):
        self.manager.current = 'home'

    def start_session(self, instance):
        try:
            target = int(self.custom_input.text.strip())
        except ValueError:
            target = 0

        live_screen = self.manager.get_screen('live_tracking')
        live_screen.target_count = target

        self.manager.current = 'live_tracking'
