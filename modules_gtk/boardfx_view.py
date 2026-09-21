import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from core.boardfx_service import BoardFXService


EFFECTS = [
    ("Solid", 0),
    ("Blink", 1),
    ("Breathe", 2),
    ("Wipe", 3),
    ("Strobe", 8),
    ("Rainbow", 9),
    ("Color Loop", 11),
    ("Chase", 28),
    ("Scan", 45),
    ("Fire", 66),
    ("Heartbeat", 101),
    ("Pacifica", 104),
]

COLOURS = {
    "Green": [0, 255, 0],
    "Red": [255, 0, 0],
    "Yellow": [255, 255, 0],
    "Blue": [0, 0, 255],
    "Purple": [128, 0, 128],
    "Orange": [255, 100, 0],
    "Cyan": [0, 255, 255],
    "Pink": [255, 0, 160],
    "White": [255, 255, 255],
}

DEFAULT_STATES = {
    "Throw": ("Solid", "Green"),
    "Takeout in progress": ("Solid", "Red"),
    "Takeout": ("Solid", "Yellow"),
    "Starting": ("Solid", "Blue"),
    "Stopped": ("Solid", "Purple"),
    "Calibrating": ("Breathe", "Purple"),
    "Error": ("Blink", "Red"),
}


class BoardFXView(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="BoardFX", tag="boardfx")
        self.window = window

        self.effect_names = [name for name, _ in EFFECTS]
        self.colour_names = list(COLOURS.keys())
        self.state_widgets = {}

        self.config = BoardFXService.load_config()

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        scrolled.set_kinetic_scrolling(True)
        self.set_child(scrolled)

        clamp = Adw.Clamp(
            maximum_size=880,
            tightening_threshold=660
        )
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(30)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)

        main = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18
        )
        clamp.set_child(main)

        title = Gtk.Label(label="BoardFX", xalign=0)
        title.add_css_class("title-1")
        title.add_css_class("pommy-title")
        main.append(title)

        subtitle = Gtk.Label(
            label="Reactive lighting for Autodarts",
            xalign=0
        )
        subtitle.add_css_class("dim-label")
        main.append(subtitle)

        # --------------------------------------------------
        # ESP32
        # --------------------------------------------------
        device_group = Adw.PreferencesGroup()
        device_group.set_title("ESP32 USB Controller")
        device_group.set_description(
            "BoardFX automatically detects supported USB serial controllers."
        )
        main.append(device_group)

        self.device_row = Adw.ActionRow()
        self.device_row.set_title("ESP32 Status")
        self.device_row.set_subtitle("Checking...")

        refresh = Gtk.Button.new_from_icon_name(
            "view-refresh-symbolic"
        )
        refresh.set_tooltip_text("Refresh USB devices")
        refresh.add_css_class("compact-btn")
        refresh.connect("clicked", lambda *_: self.refresh())
        self.device_row.add_suffix(refresh)

        device_group.add(self.device_row)

        enable_row = Adw.ActionRow()
        enable_row.set_title("Enable BoardFX")
        enable_row.set_subtitle(
            "Allow BoardFX to react to Autodarts events."
        )

        self.enable_switch = Gtk.Switch()
        self.enable_switch.set_valign(Gtk.Align.CENTER)
        self.enable_switch.set_active(
            bool(self.config.get("enabled", True))
        )
        enable_row.add_suffix(self.enable_switch)

        device_group.add(enable_row)

        self.manual_port = Adw.EntryRow()
        self.manual_port.set_title(
            "Manual USB port (optional)"
        )
        self.manual_port.set_text(
            self.config.get("manual_port", "")
        )
        device_group.add(self.manual_port)

        # --------------------------------------------------
        # BRIGHTNESS
        # --------------------------------------------------
        bright_group = Adw.PreferencesGroup()
        bright_group.set_title("Brightness")
        main.append(bright_group)

        bright_row = Adw.ActionRow()
        bright_row.set_title("Global Brightness")
        bright_row.set_subtitle(
            "Brightness used for all BoardFX effects."
        )

        self.brightness = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            1,
            255,
            1
        )
        self.brightness.set_digits(0)
        self.brightness.set_size_request(260, -1)
        self.brightness.set_valign(Gtk.Align.CENTER)
        self.brightness.set_value(
            int(self.config.get("global_brightness", 180))
        )

        bright_row.add_suffix(self.brightness)
        bright_group.add(bright_row)

        # --------------------------------------------------
        # BOARD STATES
        # --------------------------------------------------
        fx_group = Adw.PreferencesGroup()
        fx_group.set_title("Board Status Effects")
        fx_group.set_description(
            "Choose what the LEDs do for each Autodarts board state."
        )
        main.append(fx_group)

        saved_states = self.config.get("states", {})

        for state, defaults in DEFAULT_STATES.items():
            effect_default, colour_default = defaults
            saved = saved_states.get(state, {})

            row = Adw.ActionRow()
            row.set_title(state)

            controls = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8
            )
            controls.set_valign(Gtk.Align.CENTER)

            effect = Gtk.DropDown.new_from_strings(
                self.effect_names
            )
            effect.set_size_request(130, -1)

            effect_name = saved.get(
                "effect",
                effect_default
            )
            if effect_name in self.effect_names:
                effect.set_selected(
                    self.effect_names.index(effect_name)
                )

            colour = Gtk.DropDown.new_from_strings(
                self.colour_names
            )
            colour.set_size_request(110, -1)

            colour_name = saved.get(
                "colour",
                colour_default
            )
            if colour_name in self.colour_names:
                colour.set_selected(
                    self.colour_names.index(colour_name)
                )

            test = Gtk.Button(label="Test")
            test.add_css_class("compact-btn")
            test.connect(
                "clicked",
                lambda button, s=state: self._test_state(
                    s,
                    button
                )
            )

            enabled = Gtk.Switch()
            enabled.set_valign(Gtk.Align.CENTER)
            enabled.set_active(
                bool(saved.get("enabled", True))
            )

            controls.append(effect)
            controls.append(colour)
            controls.append(test)
            controls.append(enabled)

            row.add_suffix(controls)
            fx_group.add(row)

            self.state_widgets[state] = {
                "effect": effect,
                "colour": colour,
                "enabled": enabled,
            }

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------
        save = Gtk.Button(label="Save BoardFX Settings")
        save.add_css_class("suggested-action")
        save.add_css_class("touch-btn")
        save.set_size_request(-1, 54)
        save.connect("clicked", self._save)
        main.append(save)

        note = Gtk.Label(
            label=(
                "Board states first. 180, Bust, Game Win and "
                "Match Win will be added once the base controller "
                "is proven on the Wyse."
            ),
            wrap=True,
            xalign=0
        )
        note.add_css_class("dim-label")
        main.append(note)

        self.refresh()

    def _dropdown_value(self, dropdown, values):
        selected = dropdown.get_selected()

        if selected >= len(values):
            return values[0]

        return values[selected]

    def _get_state(self, state):
        widgets = self.state_widgets[state]

        return {
            "enabled": widgets["enabled"].get_active(),
            "effect": self._dropdown_value(
                widgets["effect"],
                self.effect_names
            ),
            "colour": self._dropdown_value(
                widgets["colour"],
                self.colour_names
            ),
        }

    def refresh(self):
        manual = self.manual_port.get_text().strip()
        esp = BoardFXService.find_esp32(manual)

        if esp:
            device = esp["device"]
            description = esp.get("description", "")

            if description:
                device += f" • {description}"

            self.device_row.set_subtitle(
                f"Detected: {device}"
            )
        else:
            self.device_row.set_subtitle(
                "Not detected • Connect ESP32 by USB and press Refresh"
            )

    def _save(self, *_):
        states = {}

        for state in DEFAULT_STATES:
            states[state] = self._get_state(state)

        config = {
            "enabled": self.enable_switch.get_active(),
            "manual_port": self.manual_port.get_text().strip(),
            "global_brightness": int(
                self.brightness.get_value()
            ),
            "states": states,
        }

        BoardFXService.save_config(config)
        self.config = config

        self.window.show_toast(
            "BoardFX settings saved."
        )

    def _test_state(self, state, button):
        settings = self._get_state(state)

        effect_name = settings["effect"]
        colour_name = settings["colour"]

        fx_id = dict(EFFECTS).get(
            effect_name,
            0
        )

        rgb = COLOURS.get(
            colour_name,
            [255, 255, 255]
        )

        command = {
            "on": True,
            "bri": int(self.brightness.get_value()),
            "seg": {
                "fx": fx_id,
                "col": [rgb],
            },
        }

        manual = self.manual_port.get_text().strip()
        esp = BoardFXService.find_esp32(manual)

        if not esp:
            self.window.show_toast(
                "No ESP32 detected."
            )
            return

        button.set_sensitive(False)

        def worker():
            try:
                BoardFXService.send_command(
                    esp["device"],
                    command
                )
                return True, f"{state} test sent."
            except Exception as exc:
                return False, f"BoardFX error: {exc}"

        def run():
            result = worker()
            GLib.idle_add(
                self._finish_test,
                button,
                result
            )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def _finish_test(self, button, result):
        button.set_sensitive(True)
        self.window.show_toast(result[1])
        return False
