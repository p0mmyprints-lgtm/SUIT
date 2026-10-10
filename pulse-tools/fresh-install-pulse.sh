#!/usr/bin/env bash
# Fresh PULSE install: back up and remove PULSE and everything it set up,
# then download PULSE again from GitHub and run its installer.
#
# Keeps: Autodarts (program, board login, cameras), auto-login, sudo access,
#        power settings, keyring.
#
# Usage:  bash <(curl -sL https://raw.githubusercontent.com/p0mmyprints-lgtm/SUIT/pommy-v2/pulse-tools/fresh-install-pulse.sh) [branch] [--yes]

BRANCH="pommy-v2"
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=1 ;;
    *) BRANCH="$arg" ;;
  esac
done
REPO="https://github.com/p0mmyprints-lgtm/SUIT.git"
DIR="$HOME/Pommy-SUIT"
BK="$HOME/pulse-fresh-backup-$(date +%Y%m%d-%H%M%S)"

echo "=== Fresh PULSE install (branch: $BRANCH)"
echo "This removes PULSE and its settings (rotation, touch, kiosk, launchers)"
echo "and installs it again. Autodarts and your board login are NOT touched."
echo "Everything removed is backed up to: $BK"
if [ "$ASSUME_YES" != 1 ]; then
  read -r -p "Type YES to continue: " answer < /dev/tty
  [ "$answer" = "YES" ] || { echo "Cancelled - nothing changed."; exit 0; }
fi

# Fail early if GitHub isn't reachable, before anything is removed
git ls-remote --exit-code --heads "$REPO" "$BRANCH" > /dev/null 2>&1 \
  || { echo "ERROR: can't reach branch '$BRANCH' on GitHub. Nothing was changed."; exit 1; }

mkdir -p "$BK/home" "$BK/etc"
save() {
  for p in "$@"; do
    [ -e "$p" ] || [ -L "$p" ] || continue
    rel="${p#"$HOME"/}"
    mkdir -p "$BK/home/$(dirname "$rel")"
    mv "$p" "$BK/home/$rel" && echo "    removed ~/$rel"
  done
}

echo "=== 1/5 Closing PULSE, the kiosk browser and BoardFX"
pkill -f "Pommy-SUIT/app_gtk.py"
pkill -f "suit/kiosk_extension"
systemctl --user disable --now pulse-boardfx.service 2> /dev/null
sleep 1

echo "=== 2/5 Removing PULSE files"
save "$DIR" "$HOME/.local/share/suit" "$HOME/.config/suit" "$HOME/.config/pommy-autodarts" \
     "$HOME/.suit_rotation_config.json" "$HOME/.config/monitors.xml" \
     "$HOME/.config/autostart/suit-kiosk.desktop" "$HOME/.config/autostart/suit-rotation.desktop" \
     "$HOME/.config/autostart/suit-chromium.desktop" \
     "$HOME/.config/systemd/user/pulse-boardfx.service" \
     "$HOME/.config/systemd/user/default.target.wants/pulse-boardfx.service" \
     "$HOME/.local/share/applications/de.iterathor.suit.gtk.desktop" \
     "$HOME/.local/share/applications/SUIT.desktop" \
     "$HOME/.suit.lock" "$HOME"/.pommypc*
if grep -q "suit" "$HOME/.local/share/applications/chromium-browser.desktop" 2> /dev/null; then
  save "$HOME/.local/share/applications/chromium-browser.desktop"
fi
for d in chromium google-chrome BraveSoftware/Brave-Browser; do
  save "$HOME/.config/$d/NativeMessagingHosts/com.suit.kiosk.json"
done
rm -f "$HOME"/.local/share/icons/hicolor/*/apps/de.iterathor.suit.gtk.png \
      "$HOME"/.local/share/icons/hicolor/*/apps/suit-icon.png
systemctl --user daemon-reload
update-desktop-database "$HOME/.local/share/applications" 2> /dev/null

echo "=== 3/5 Removing PULSE system settings (may ask for your password)"
if [ -f /etc/udev/rules.d/99-suit-touch.rules ]; then
  sudo cp /etc/udev/rules.d/99-suit-touch.rules "$BK/etc/" \
    && sudo rm -f /etc/udev/rules.d/99-suit-touch.rules \
    && sudo udevadm control --reload-rules \
    && echo "    removed touch calibration"
fi
if grep -q "SUIT Autodarts In-Page Controls" /etc/chromium/chromium.conf 2> /dev/null; then
  sudo cp /etc/chromium/chromium.conf "$BK/etc/" \
    && sudo sed -i '/# >>> SUIT Autodarts In-Page Controls >>>/,/# <<< SUIT Autodarts In-Page Controls <<</d' /etc/chromium/chromium.conf \
    && echo "    removed kiosk extension from chromium.conf"
fi
if [ -f /etc/chromium/native-messaging-hosts/com.suit.kiosk.json ]; then
  sudo mv /etc/chromium/native-messaging-hosts/com.suit.kiosk.json "$BK/etc/" \
    && echo "    removed system kiosk host"
fi
sudo chown -R "$USER:" "$BK"
favs=$(gsettings get org.gnome.shell favorite-apps 2> /dev/null)
if [ -n "$favs" ]; then
  gsettings set org.gnome.shell favorite-apps "$(python3 -c 'import sys, ast; print([a for a in ast.literal_eval(sys.argv[1]) if a not in ("de.iterathor.suit.gtk.desktop", "SUIT.desktop")])' "$favs")"
fi

echo "=== 4/5 Downloading PULSE ($BRANCH)"
if ! git clone -b "$BRANCH" "$REPO" "$DIR"; then
  echo "ERROR: download failed. Your old PULSE is in $BK/home/Pommy-SUIT"
  exit 1
fi

echo "=== 5/5 Running the PULSE installer"
cd "$DIR" && bash install.sh
# The desktop wallpaper PULSE set lives in ~/.local/share/suit, which was backed up
# above: put the image back so the desktop doesn't fall back to Fedora's default
mkdir -p "$HOME/.local/share/suit"
cp "$DIR/assets/wallpaper_stealth_grey_pattern_ultrasubtle.png" "$HOME/.local/share/suit/" 2> /dev/null

echo
echo "=== DONE"
echo "PULSE was reinstalled from '$BRANCH'. Autodarts was not touched."
echo "Backup of the old PULSE and its settings: $BK"
echo "Restart the PC, then set up screen rotation, touch and kiosk again in PULSE."
