#!/usr/bin/env bash
# Save your PULSE changes to GitHub.
cd "$HOME/Pommy-SUIT" || { echo "ERROR: ~/Pommy-SUIT not found"; read -r -p "Press Enter to close..."; exit 1; }

echo "=== Saving PULSE to GitHub ==="

if [ -n "$(git status --porcelain)" ]; then
  echo "Changed files:"
  git status --short
  echo
  read -r -p "What did you change? " MSG
  [ -z "$MSG" ] && MSG="Update PULSE"
  git add -A
  git commit -m "$MSG" || { echo "ERROR: commit failed"; read -r -p "Press Enter to close..."; exit 1; }
else
  echo "No new changes - pushing any saved commits."
fi

if git push origin pommy-v2 pommy-v2:main; then
  echo
  echo "=== DONE - saved to GitHub as $(git rev-parse --short HEAD) ==="
else
  echo
  echo "ERROR: push failed. If it asked for a password, use a GitHub token, not your password."
fi
read -r -p "Press Enter to close..."
