import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import sys
import json
import logging
import subprocess
import fcntl
import time
import importlib.metadata

# Paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
LOG_FILE = BASE_DIR / "pommypc.log"
CONFIG_FILE = Path.home() / ".pommypc_config.json"
lock_file = Path.home() / ".pommypc.lock"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global Exception Handler
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = global_exception_handler

# Single Instance Lock
lock_fp = open(lock_file, 'w')
try:
    fcntl.lockf(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Pommy PC Setup is already running.")
    sys.exit(0)

from modules.utils import ServiceUtils

# Import modules
from modules.menu import MainMenu
from modules.autodarts import AutodartsView
from modules.autoglow import AutoGlowView
from modules.kiosk import KioskView
from modules.usb_bandwidth import UsbBandwidthView

# Optional Rotation
try:
    from modules.rotation import RotationView
except ImportError:
    RotationView = None
    logger.warning("RotationView module could not be imported.")

# Set appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class PommyPCApp(ctk.CTk):
    def report_callback_exception(self, exc, val, tb):
        logger.error("Unhandled UI exception:", exc_info=(exc, val, tb))

    def __init__(self):
        super().__init__()
        self.withdraw()
        logger.info("Starting Pommy PC Setup...")
        self.title("Pommy PC - Autodarts Setup")

        self.minsize(800, 650)
        self.project_dir = BASE_DIR

        # Pommy Prints Palette — black, green, red
        self.colors = {
            "bg": "#0f0f0f",        # Near black
            "card": "#1a1a1a",      # Dark card
            "header": "#2a2a2a",    # Slightly lighter
            "accent": "#16a34a",    # Pommy green
            "success": "#22c55e",   # Lighter green for status
            "danger": "#dc2626",    # Pommy red
            "warning": "#eab308",   # Yellow (keep for warnings)
            "fg": "#ffffff",        # White text
            "fg_dim": "#a1a1aa"     # Dimmed text
        }

        # No language switcher — English only
        self.lang = "en"
        self.texts = {}
        self.load_translations()

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("green")

        # --- FRAME LOADING ---
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True, padx=20, pady=20)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # --- BRANDING BADGE (top right, replaces language switcher) ---
        self.brand_lbl = ctk.CTkLabel(self, text="🖨 Pommy Prints", width=140, height=32,
                                      fg_color=self.colors["card"],
                                      corner_radius=8,
                                      text_color=self.colors["accent"],
                                      font=("Roboto", 11, "bold"))
        self.brand_lbl.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=20)

        self.frames = {}

        # Load views — IteraThor module removed
        views = [AutodartsView, AutoGlowView, KioskView, UsbBandwidthView]
        if RotationView:
            views.append(RotationView)
        views.append(MainMenu)

        for F in views:
            try:
                frame = F(self.container, self)
                self.frames[F] = frame
                frame.grid(row=0, column=0, sticky="nsew")
            except Exception as e:
                logger.error(f"Error loading {F.__name__}: {e}")

        self.show_menu()
        self.start_polling()
        self.deiconify()
        self.after(1000, self.check_initial_setup)

    def check_initial_setup(self):
        if not ServiceUtils.check_sudo_nopasswd():
            ServiceUtils.setup_sudo_nopasswd(self)
        self.check_requirements()

    def start_polling(self):
        self.poll_services()

    def poll_services(self):
        try:
            for frame in self.frames.values():
                if frame.winfo_viewable() and hasattr(frame, "update_status"):
                    frame.update_status()
                    break
        except Exception as e:
            pass
        self.after(5000, self.poll_services)

    def check_requirements(self):
        req_file = BASE_DIR / "requirements.txt"
        if not req_file.exists():
            return

        missing = []
        with open(req_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                try:
                    importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    missing.append(line)

        if missing:
            msg = f"Missing packages:\n{chr(10).join(missing)}\n\nInstall now?"
            if messagebox.askyesno("Pommy PC Setup", msg):
                pkgs = " ".join(missing)
                in_venv = sys.prefix != sys.base_prefix
                install_cmd = f"{sys.executable} -m pip install {pkgs}"
                if not in_venv:
                    install_cmd = ServiceUtils.sudo_cmd(install_cmd)
                logger.info(f"Installing: {pkgs}")
                ServiceUtils.run_bash_script(self, install_cmd, title="Installing packages", on_close=self.check_requirements)

    def load_translations(self):
        # Keep lang.json support for any modules that still reference it
        lang_path = BASE_DIR / "lang.json"
        try:
            with open(lang_path, "r") as f:
                self.texts = json.load(f)
        except Exception as e:
            logger.warning(f"lang.json not found or unreadable: {e}")
            self.texts = {}

    def refresh_ui(self):
        for frame in self.frames.values():
            if hasattr(frame, "update_texts"):
                frame.update_texts()
        self.brand_lbl.lift()

    def show_frame(self, cont):
        if cont in self.frames:
            frame = self.frames[cont]
            frame.tkraise()
            self.brand_lbl.lift()
            if hasattr(frame, "update_texts"):
                frame.update_texts()
            if hasattr(frame, "update_status"):
                frame.update_status()

    def show_menu(self):       self.show_frame(MainMenu)
    def show_autodarts(self):  self.show_frame(AutodartsView)
    def show_autoglow(self):   self.show_frame(AutoGlowView)
    def show_kiosk(self):      self.show_frame(KioskView)
    def show_usb(self):        self.show_frame(UsbBandwidthView)
    def show_touch(self):
        if RotationView:
            self.show_frame(RotationView)
        else:
            logger.warning("RotationView missing.")



if __name__ == "__main__":
    app = PommyPCApp()
    app.mainloop()
