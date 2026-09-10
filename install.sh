#!/bin/bash

# ============================================
#   Pommy PC - Autodarts Setup Installer
#   pommyprints.com.au
# ============================================

set -e

echo ""
echo "============================================"
echo "   Pommy PC - Autodarts Setup Installer"
echo "   pommyprints.com.au"
echo "============================================"
echo ""

# Detect Distribution
if [ -f /etc/fedora-release ]; then
    DISTRO="fedora"
elif [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
    DISTRO="debian"
else
    echo "[!] Unsupported distribution. Please install dependencies manually."
    DISTRO="unknown"
fi

echo "[*] Detected OS: $DISTRO"
echo ""

# 1. Install system dependencies
echo "[*] Installing system dependencies..."

if [ "$DISTRO" == "fedora" ]; then
    sudo dnf install -y python3-tkinter python3-dbus python3-devel dbus-devel \
    glib2-devel gcc gcc-c++ make pkgconf-pkg-config libX11-devel libxcb-devel \
    libXext-devel libXrender-devel xrandr git chromium

    # Add user to input group for hardware access (kill-switch)
    sudo usermod -aG input $USER
    echo "[*] Added $USER to 'input' group. A re-login may be required."

elif [ "$DISTRO" == "debian" ]; then
    sudo apt update
    sudo apt install -y python3-tk python3-dbus python3-venv python3-dev \
    libdbus-1-dev git libxcb-cursor0 libglib2.0-dev build-essential pkg-config \
    x11-xserver-utils chromium-browser
fi

echo ""
echo "[*] System dependencies installed."
echo ""

# 2. Set up Python environment and launcher
echo "[*] Setting up Python environment and launcher..."
cd "$(dirname "$0")"
python3 create_launcher.py

echo ""
echo "============================================"
echo "  [+] Pommy PC Setup installed successfully!"
echo "  Launch from your desktop or app menu."
echo "============================================"
echo ""
