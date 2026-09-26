#!/usr/bin/env bash
# Copy the latest PULSE commit to a USB stick as a .patch file.
cd "$HOME/Pommy-SUIT" || { echo "ERROR: ~/Pommy-SUIT not found"; read -r -p "Press Enter to close..."; exit 1; }

USB=$(find "/run/media/$USER" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1)
if [ -z "$USB" ]; then
  echo "ERROR: No USB found. Connect it to the VM first (VirtualBox: Devices > USB)."
  read -r -p "Press Enter to close..."
  exit 1
fi

COMMIT=$(git rev-parse --short HEAD)
OUT="$USB/pulse-$COMMIT.patch"

if git show --format=email --binary HEAD > "$OUT" && [ -s "$OUT" ]; then
  echo "DONE - saved $OUT ($(stat -c%s "$OUT") bytes)"
else
  rm -f "$OUT"
  echo "ERROR: export failed"
fi
read -r -p "Press Enter to close..."
