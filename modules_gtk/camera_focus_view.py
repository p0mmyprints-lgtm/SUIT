"""Camera Focus: frees the cameras and opens the DartCam Focus Station web tool.

PULSE used to ship its own focus tool built on OpenCV, which pulled in about
800 MB of libraries (VTK, OpenCASCADE, OpenBLAS, GDAL...) and reserved 16 GB of
address space. The community DartCam Focus Station does the same job in the
browser (Laplacian / Tenengrad / Brenner focus score on a Siemens star), so
PULSE now only pauses Autodarts while it runs and opens the page.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from core.logger import get_logger
from core.systemd_service import SystemdService
from modules_gtk.async_utils import run_async, open_browser_url
from modules_gtk.ui_helpers import create_button_with_icon

logger = get_logger("camera_focus_view")

FOCUS_STATION_URL = "https://zoofly85.github.io/dart-focus-station/"
SERVICE_NAME = "autodarts.service"

STEPS = [
    ("Print the Siemens star",
     "Download it from the Focus Station page and mount it flat, level with the board."),
    ("Open Focus Station",
     "Allow camera access, pick a camera and click the centre of the star in the live picture."),
    ("Turn the focus ring",
     "Until the Focus Score stays at 80 or above. Do each camera, then lock or tape the rings."),
    ("Close the browser tab",
     "Then tap Done so Autodarts gets its cameras back."),
]


class CameraFocusView(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="Camera Focus Tool", tag="camera_focus")
        self.window = window
        # True while PULSE is holding Autodarts stopped so the browser can use the cameras
        self.paused_autodarts = False

        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.set_child(scrolled)

        clamp = Adw.Clamp(maximum_size=760)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        title = Gtk.Label(label="Camera Focus", xalign=0)
        title.add_css_class("title-1")
        box.append(title)

        intro = Gtk.Label(
            label="Focus each camera with the DartCam Focus Station in the browser. "
                  "Autodarts is paused while you do this, because a camera can only be "
                  "used by one program at a time.",
            xalign=0, wrap=True,
        )
        intro.add_css_class("dim-label")
        box.append(intro)

        steps = Adw.PreferencesGroup(title="How to focus")
        for i, (step_title, step_text) in enumerate(STEPS, 1):
            row = Adw.ActionRow(title=f"{i}. {step_title}", subtitle=step_text)
            row.set_subtitle_lines(0)
            steps.add(row)
        box.append(steps)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_homogeneous(True)
        self.btn_open = create_button_with_icon(
            "web-browser-symbolic", "Open Focus Station", "suggested-action", height=50, touch_btn=True)
        self.btn_open.connect("clicked", self._on_open_clicked)
        self.btn_done = create_button_with_icon(
            "object-select-symbolic", "Done, restart Autodarts", "secondary-btn", height=50, touch_btn=True)
        self.btn_done.connect("clicked", self._on_done_clicked)
        buttons.append(self.btn_open)
        buttons.append(self.btn_done)
        box.append(buttons)

        self.lbl_status = Gtk.Label(xalign=0, wrap=True)
        self.lbl_status.add_css_class("dim-label")
        box.append(self.lbl_status)

        self._refresh_buttons()

    def _refresh_buttons(self):
        self.btn_done.set_sensitive(self.paused_autodarts)
        if self.paused_autodarts:
            self.lbl_status.set_text(
                "Autodarts is paused. When you have finished, close the Focus Station tab "
                "and tap Done. Leaving this screen also restarts Autodarts.")
        else:
            self.lbl_status.set_text("Focus Station needs an internet connection.")

    def on_page_opened(self):
        self._refresh_buttons()

    def _on_open_clicked(self, btn):
        btn.set_sensitive(False)

        def pause():
            if SystemdService.is_unit_active(SERVICE_NAME):
                return SystemdService.stop_unit(SERVICE_NAME)
            return None  # Autodarts wasn't running: nothing to pause

        def on_done(stopped):
            btn.set_sensitive(True)
            if stopped is False:
                self.window.show_toast("Couldn't pause Autodarts - the cameras may be busy.")
            elif stopped:
                self.paused_autodarts = True
            self._refresh_buttons()
            if not open_browser_url(self.window, FOCUS_STATION_URL):
                self.window.show_toast("Couldn't open the browser.")

        run_async(pause, on_done=on_done)

    def _resume_autodarts(self):
        if not self.paused_autodarts:
            return
        self.paused_autodarts = False
        self._refresh_buttons()

        def on_done(ok):
            self.window.show_toast(
                "Autodarts restarted." if ok else "Couldn't restart Autodarts - try Restart in Autodarts Setup.")

        run_async(lambda: SystemdService.start_unit(SERVICE_NAME), on_done=on_done)

    def _on_done_clicked(self, btn):
        self._resume_autodarts()
        self.window.nav_view.pop()

    def on_page_closed(self):
        """Called by the window when navigating away: never leave Autodarts stopped."""
        self._resume_autodarts()
