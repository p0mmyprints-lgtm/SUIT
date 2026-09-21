import json
import time
from pathlib import Path

import serial
import serial.tools.list_ports


KNOWN_VID_PIDS = {
    (0x10C4, 0xEA60),  # CP210x
    (0x1A86, 0x7523),  # CH340
    (0x0403, 0x6001),  # FTDI
    (0x303A, 0x1001),  # Espressif
}

BAUD_RATE = 115200

CONFIG_DIR = Path.home() / ".config" / "pommy-autodarts"
CONFIG_FILE = CONFIG_DIR / "boardfx.json"


class BoardFXService:
    @staticmethod
    def list_serial_ports():
        ports = []

        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description or "",
                "vid": port.vid,
                "pid": port.pid,
                "known_esp32": (port.vid, port.pid) in KNOWN_VID_PIDS,
            })

        return ports

    @classmethod
    def find_esp32(cls, manual_port=""):
        if manual_port:
            for port in cls.list_serial_ports():
                if port["device"] == manual_port:
                    return port

        for port in cls.list_serial_ports():
            if port["known_esp32"]:
                return port

        return None

    @staticmethod
    def send_command(port, command):
        with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
            time.sleep(1.5)
            ser.write((json.dumps(command) + "\n").encode("utf-8"))
            ser.flush()

    @classmethod
    def test_light(cls, port, brightness=180):
        command = {
            "on": True,
            "bri": int(brightness),
            "seg": {
                "fx": 0,
                "col": [[0, 255, 0]]
            }
        }

        cls.send_command(port, command)

    @staticmethod
    def load_config():
        defaults = {
            "enabled": True,
            "manual_port": "",
            "global_brightness": 180,
        }

        if not CONFIG_FILE.exists():
            return defaults

        try:
            saved = json.loads(CONFIG_FILE.read_text())
            defaults.update(saved)
        except Exception:
            pass

        return defaults

    @staticmethod
    def save_config(config):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=4))
