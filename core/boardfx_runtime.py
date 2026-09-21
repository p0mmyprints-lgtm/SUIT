import asyncio
import json
import logging

import serial
import websockets

from core.boardfx_service import BoardFXService, BAUD_RATE


AUTODARTS_EVENTS = "ws://localhost:3180/api/events"

EFFECT_IDS = {
    "Solid": 0,
    "Blink": 1,
    "Breathe": 2,
    "Wipe": 3,
    "Strobe": 8,
    "Rainbow": 9,
    "Color Loop": 11,
    "Chase": 28,
    "Scan": 45,
    "Fire": 66,
    "Heartbeat": 101,
    "Pacifica": 104,
}

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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BoardFX] %(levelname)s: %(message)s",
)

logger = logging.getLogger("pulse.boardfx")


class BoardFXRuntime:
    def __init__(self):
        self.serial = None
        self.serial_port = None

    def close_serial(self):
        if self.serial:
            try:
                if self.serial.is_open:
                    self.serial.close()
            except Exception:
                pass

        self.serial = None
        self.serial_port = None

    async def ensure_serial(self):
        config = BoardFXService.load_config()

        if not config.get("enabled", True):
            self.close_serial()
            return False

        manual = config.get("manual_port", "").strip()
        esp = BoardFXService.find_esp32(manual)

        if not esp:
            self.close_serial()
            return False

        port = esp["device"]

        if (
            self.serial
            and self.serial.is_open
            and self.serial_port == port
        ):
            return True

        self.close_serial()

        try:
            logger.info("Opening ESP32 on %s", port)

            self.serial = serial.Serial(
                port,
                BAUD_RATE,
                timeout=1,
                write_timeout=1,
            )

            self.serial_port = port

            # Some ESP32 boards reset when the serial port opens.
            await asyncio.sleep(2)

            logger.info("ESP32 connected on %s", port)
            return True

        except Exception as exc:
            logger.warning(
                "Unable to open ESP32 on %s: %s",
                port,
                exc,
            )

            self.close_serial()
            return False

    def build_state_command(self, status):
        config = BoardFXService.load_config()

        if not config.get("enabled", True):
            return None

        state = config.get("states", {}).get(status)

        if not state:
            return None

        if not state.get("enabled", True):
            return None

        effect_name = state.get("effect", "Solid")
        colour_name = state.get("colour", "White")

        brightness = int(
            config.get("global_brightness", 180)
        )
        brightness = max(1, min(255, brightness))

        return {
            "on": True,
            "bri": brightness,
            "seg": {
                "fx": EFFECT_IDS.get(effect_name, 0),
                "col": [
                    COLOURS.get(
                        colour_name,
                        [255, 255, 255],
                    )
                ],
            },
        }

    async def send_state(self, status):
        command = self.build_state_command(status)

        if command is None:
            logger.debug(
                "Ignoring unconfigured/disabled state: %s",
                status,
            )
            return

        if not await self.ensure_serial():
            logger.warning(
                "State '%s' received but no ESP32 is available.",
                status,
            )
            return

        try:
            payload = json.dumps(command) + "\n"

            self.serial.write(
                payload.encode("utf-8")
            )
            self.serial.flush()

            logger.info(
                "Autodarts state -> %s",
                status,
            )

        except Exception as exc:
            logger.warning(
                "ESP32 write failed: %s",
                exc,
            )

            self.close_serial()

    async def run(self):
        logger.info("PULSE BoardFX runtime started.")

        while True:
            try:
                logger.info(
                    "Connecting to Autodarts events..."
                )

                async with websockets.connect(
                    AUTODARTS_EVENTS,
                    ping_interval=20,
                    ping_timeout=20,
                ) as websocket:

                    logger.info(
                        "Connected to Autodarts at %s",
                        AUTODARTS_EVENTS,
                    )

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            continue

                        if data.get("type") != "state":
                            continue

                        event_data = data.get("data", {})
                        status = event_data.get("status")

                        if isinstance(status, str):
                            await self.send_state(status)

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                logger.warning(
                    "Autodarts connection unavailable: %s",
                    exc,
                )

                await asyncio.sleep(5)

    async def shutdown(self):
        self.close_serial()


async def main():
    runtime = BoardFXRuntime()

    try:
        await runtime.run()
    finally:
        await runtime.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
