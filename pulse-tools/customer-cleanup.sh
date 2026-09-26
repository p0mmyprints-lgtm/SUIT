#!/usr/bin/env bash
# Tidy a customer PC: hide unwanted apps, install GNOME Text Editor.

echo "=== PULSE customer cleanup ==="
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"

# Apps to hide (matched against the contents of each app's .desktop file)
HIDE='DRAWEXE|opencascade|^Exec=gnome-software'

echo "1/2 Hiding unwanted apps..."
hidden=()
for f in /usr/share/applications/*.desktop /usr/local/share/applications/*.desktop \
         /var/lib/flatpak/exports/share/applications/*.desktop "$APPS"/*.desktop; do
  [ -f "$f" ] || continue
  grep -qiE "$HIDE" "$f" || continue
  name=$(basename "$f")
  tmp=$(mktemp)
  sed -e '/^NoDisplay=/d' -e '/^Hidden=/d' -e '/^\[Desktop Entry\]/a NoDisplay=true' "$f" > "$tmp"
  mv "$tmp" "$APPS/$name"
  echo "   Hidden: $name"
  hidden+=("$name")
done
[ ${#hidden[@]} = 0 ] && echo "   Nothing to hide (already gone?)"
update-desktop-database "$APPS" 2>/dev/null || true

# Also remove them from the dock
if [ ${#hidden[@]} -gt 0 ] && command -v gsettings >/dev/null; then
  favs=$(gsettings get org.gnome.shell favorite-apps)
  newfavs=$(python3 -c 'import sys,ast; f=ast.literal_eval(sys.argv[1]); print([a for a in f if a not in sys.argv[2:]])' "$favs" "${hidden[@]}")
  gsettings set org.gnome.shell favorite-apps "$newfavs"
fi

echo "2/2 Installing GNOME Text Editor..."
sudo dnf install -y gnome-text-editor

echo
echo "=== DONE ==="
read -r -p "Press Enter to close..."
