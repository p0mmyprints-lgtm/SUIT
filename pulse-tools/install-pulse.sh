#!/usr/bin/env bash
# Install (or update) PULSE on a Fedora PC.
set -e

REPO="https://github.com/p0mmyprints-lgtm/SUIT.git"
DIR="$HOME/Pommy-SUIT"

echo "=== Installing PULSE ==="
sudo dnf install -y git

if [ -d "$DIR/.git" ]; then
  echo "PULSE already downloaded - updating..."
  git -C "$DIR" pull origin pommy-v2
else
  git clone -b pommy-v2 "$REPO" "$DIR"
fi

cd "$DIR"
chmod +x install.sh
./install.sh

echo
echo "=== DONE - PULSE installed ==="
read -r -p "Press Enter to close..."
