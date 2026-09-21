#!/usr/bin/env bash
set -e

echo "========================================="
echo "   SUIT for Fedora - Automated Setup    "
echo "========================================="

# 1. Check Fedora environment
if [ ! -f /etc/fedora-release ]; then
    echo "Warning: /etc/fedora-release not detected. SUIT is optimized for Fedora Linux."
fi

# 2. Clean up legacy SUIT artifacts if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/uninstall_legacy.sh" ]; then
    "${SCRIPT_DIR}/uninstall_legacy.sh"
fi

# 3. Install native system dependencies via DNF
echo "[1/4] Installing system packages..."
sudo dnf install -y --setopt=install_weak_deps=False \
    python3 \
    python3-gobject \
    libadwaita \
    python3-dbus \
    python3-evdev \
    python3-pyserial \
    python3-websockets \
    python3-qrcode \
    python3-opencv \
    git

# 4. Create Application and Desktop Launchers
echo "[2/4] Generating desktop and menu launchers..."
python3 "${SCRIPT_DIR}/create_launcher.py"

# 5. Install and enable PULSE BoardFX user service
echo "[3/4] Installing PULSE BoardFX background service..."

USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
mkdir -p "${USER_SYSTEMD_DIR}"

cat > "${USER_SYSTEMD_DIR}/pulse-boardfx.service" <<EOF
[Unit]
Description=PULSE BoardFX - Reactive lighting for Autodarts

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 -m core.boardfx_runtime
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now pulse-boardfx.service

# 6. Success confirmation
echo "[4/4] Installation completed successfully!"
echo "========================================="
echo "PULSE is now installed and ready to use."
echo "Launch PULSE from your application menu or Dash favorites."
echo "========================================="
