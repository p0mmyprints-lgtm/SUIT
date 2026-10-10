"""Free up disk space safely.

Small drives (like a 13 GB eMMC) fill up with Fedora's background update
downloads, package caches, crash reports and logs. This only clears data that
is re-created or re-downloaded when needed: nothing installed is removed.
"""

import shutil
import subprocess
from pathlib import Path

from core.logger import get_logger

logger = get_logger("storage")

JOURNAL_CAP_CONF = "/etc/systemd/journald.conf.d/10-size-cap.conf"


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(total, free) bytes of the drive holding `path`."""
    usage = shutil.disk_usage(path)
    return usage.total, usage.free


def human(num_bytes: int) -> str:
    gb = num_bytes / 1024 ** 3
    return f"{gb:.1f} GB" if gb >= 1 else f"{num_bytes / 1024 ** 2:.0f} MB"


def _sudo(*args: str, input_text: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "-n", *args], input=input_text, capture_output=True,
                          text=True, timeout=timeout)


def free_up_space() -> tuple[bool, str]:
    _, free_before = disk_usage()
    try:
        # 1. Leftover update downloads - only when no update is scheduled to use them
        status = _sudo("dnf5", "offline", "status").stdout
        if "No offline transaction is stored" in status:
            _sudo("dnf5", "offline", "clean")

        # 2. Package caches (re-downloaded when needed)
        _sudo("dnf5", "clean", "all")
        for cache_dir in ("/var/cache/PackageKit", "/var/cache/dnf5daemon-server"):
            _sudo("find", cache_dir, "-mindepth", "1", "-delete")

        # 3. Crash reports
        _sudo("find", "/var/spool/abrt", "-mindepth", "1", "-maxdepth", "1", "-type", "d",
              "-name", "ccpp-*", "-exec", "rm", "-rf", "{}", "+")

        # 4. System logs: keep at most 100 MB from now on, and trim now
        _sudo("mkdir", "-p", str(Path(JOURNAL_CAP_CONF).parent))
        _sudo("tee", JOURNAL_CAP_CONF, input_text="[Journal]\nSystemMaxUse=100M\n")
        _sudo("systemctl", "restart", "systemd-journald")
        _sudo("journalctl", "--rotate")
        _sudo("journalctl", "--vacuum-size=100M")

        # 5. GNOME Software's cache (rebuilt automatically)
        shutil.rmtree(Path.home() / ".cache" / "gnome-software", ignore_errors=True)

        # 6. Stop GNOME Software downloading big updates in the background
        subprocess.run(["gsettings", "set", "org.gnome.software", "download-updates", "false"],
                       capture_output=True, timeout=10)
    except Exception as e:
        logger.exception("Free up space failed")
        return False, f"Clean-up stopped: {e}"

    _, free_after = disk_usage()
    freed = max(0, free_after - free_before)
    logger.info("Free up space: freed %s, %s free now", human(freed), human(free_after))
    return True, f"Freed {human(freed)}. {human(free_after)} free now."
