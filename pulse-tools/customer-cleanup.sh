#!/usr/bin/env bash
# Tidy a customer PC: hide OpenCASCADE Draw, install a text editor.
set -e

echo "=== PULSE customer cleanup ==="

rm -f "$HOME/.local/share/applications/DRAWEXE.desktop"
mkdir -p "$HOME/.local/share/applications"
printf '[Desktop Entry]\nHidden=true\n' > "$HOME/.local/share/applications/opencascade-draw.desktop"
echo "OpenCASCADE Draw hidden."

sudo dnf install -y gnome-text-editor
echo "GNOME Text Editor installed."

echo
echo "=== DONE ==="
read -r -p "Press Enter to close..."
