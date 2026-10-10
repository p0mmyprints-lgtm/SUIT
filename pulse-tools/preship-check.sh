#!/usr/bin/env bash
# PULSE pre-ship checklist: run on a PC before it goes to a customer.
# READ-ONLY: it only checks and reports, it changes nothing.
#
#   bash ~/Pommy-SUIT/pulse-tools/preship-check.sh
#
# A copy of the report is saved as ~/preship-report-<date>.txt

DIR="$HOME/Pommy-SUIT"
REPORT="$HOME/preship-report-$(date +%Y%m%d-%H%M).txt"
CFG="$HOME/.config/autodarts/config.toml"
PASS=0; WARN=0; FAIL=0

# When run over SSH, borrow the desktop session's bus so gsettings reads the real values
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
  SP=$(pgrep -u "$USER" -x gnome-shell | head -1)
  [ -n "$SP" ] && export "$(tr '\0' '\n' < /proc/$SP/environ | grep '^DBUS_SESSION_BUS_ADDRESS=')"
fi

ok()   { echo "  ✔ $1"; PASS=$((PASS + 1)); }
warn() { echo "  ! $1"; WARN=$((WARN + 1)); }
bad()  { echo "  ✘ $1"; FAIL=$((FAIL + 1)); }
section() { echo; echo "== $1"; }

{
echo "PULSE pre-ship checklist - $(hostname) - $(date '+%d %b %Y %H:%M')"

section "PULSE"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch -q origin 2> /dev/null
  HEAD=$(git -C "$DIR" rev-parse --short HEAD); LIVE=$(git -C "$DIR" rev-parse --short origin/main 2> /dev/null)
  if [ "$HEAD" = "$LIVE" ]; then ok "Latest version ($HEAD)"; else warn "Version $HEAD, latest is $LIVE - tap Check for Updates"; fi
  [ -z "$(git -C "$DIR" status --porcelain --untracked-files=no)" ] && ok "No local code changes" || warn "Local code changes present"
else
  bad "PULSE not installed in $DIR"
fi
[ -f "$HOME/.local/share/applications/de.iterathor.suit.gtk.desktop" ] && ok "Menu launcher" || bad "Menu launcher missing"

section "Autodarts"
if [ -x "$HOME/.local/share/autodarts/autodarts" ]; then ok "Installed (v2)"; else bad "Autodarts v2 not installed"; fi
[ "$(systemctl --user is-active autodarts 2> /dev/null)" = "active" ] && ok "Service running" || bad "Service not running"
[ "$(systemctl --user is-enabled autodarts 2> /dev/null)" = "enabled" ] && ok "Starts at boot" || bad "Not set to start at boot"
[ "$(loginctl show-user "$USER" -p Linger --value 2> /dev/null)" = "yes" ] && ok "Starts before anyone logs in (linger)" || warn "Linger off - Autodarts only starts after login"
VER=$(curl -s -m 3 localhost:3180/api/version || curl -s -m 3 localhost:3182/api/version)
LATEST=$(curl -s -m 5 https://releases.autodarts.com/headless/downloads/latest.stable.json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["platforms"]["linux-amd64"]["version"])' 2> /dev/null)
if [ -z "$VER" ]; then bad "Not answering on its local API"
elif [ -n "$LATEST" ] && [ "$VER" != "$LATEST" ]; then warn "Version $VER, latest is $LATEST"
else ok "Version $VER"; fi
PYOUT=$(python3 - "$CFG" <<'PY'
import sys, tomllib, os, re, json, urllib.request
def ok(m): print(f"  ✔ {m}")
def warn(m): print(f"  ! {m}")
def bad(m): print(f"  ✘ {m}")
try:
    cfg = tomllib.load(open(sys.argv[1], "rb"))
except Exception:
    bad("No Autodarts settings file"); sys.exit()
up = cfg.get("upstream") or cfg.get("auth") or {}
ok("Board linked") if up.get("board_id") and up.get("api_key") else bad("Board NOT linked")
cam = cfg.get("cam", {})
devs = [d for d in (cam.get("devices") or cam.get("cams") or []) if d]
nodes = [ (re.search(r"/dev/video\d+", d) or [d])[0] for d in devs ]
if len(devs) == 3: ok("3 cameras configured")
else: bad(f"{len(devs)} camera(s) configured - Autodarts needs 3")
if len(set(nodes)) < len(nodes): bad(f"The same camera is selected twice: {nodes}")
missing = [n for n in nodes if not os.path.exists(n)]
if missing: bad(f"Configured camera(s) not connected: {missing}")
print(f"      resolution {cam.get('width')}x{cam.get('height')} @ {cam.get('fps')} fps")
try:
    fps = json.load(urllib.request.urlopen("http://localhost:3180/api/cams/stats", timeout=3)).get("fps", [])
    live = [round(f) for f in fps]
    if fps and all(f > 5 for f in fps) and len(fps) >= 3: ok(f"All cameras streaming {live} fps")
    else: warn(f"Camera stream rates {live} fps - check cameras / USB")
except Exception:
    warn("Couldn't read live camera stats")
PY
)
echo "$PYOUT"
PASS=$((PASS + $(grep -c '^  ✔' <<< "$PYOUT")))
WARN=$((WARN + $(grep -c '^  !' <<< "$PYOUT")))
FAIL=$((FAIL + $(grep -c '^  ✘' <<< "$PYOUT")))

section "Always-on setup"
grep -q "^AutomaticLoginEnable=True" /etc/gdm/custom.conf 2> /dev/null && ok "Automatic login" || bad "Automatic login is off"
[ "$(gsettings get org.gnome.desktop.session idle-delay 2> /dev/null)" = "uint32 0" ] && ok "Screen never blanks" || bad "Screen blanks when idle"
[ "$(gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 2> /dev/null)" = "'nothing'" ] && ok "Never goes to sleep" || bad "Goes to sleep when idle"
if (cd "$DIR" 2> /dev/null && python3 -c 'import sys; sys.path.insert(0, "."); from core.keyring_service import KeyringService as K; sys.exit(0 if K.is_keyring_blank_or_unlocked()[0] else 1)' 2> /dev/null); then
  ok "Keyring unlocks at boot (needed for Remote Desktop)"
else
  warn "Keyring has a password - Remote Desktop may refuse after a restart"
fi

section "Storage"
TOTAL=$(df -BG --output=size / | tail -1 | tr -dc 0-9); FREE=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
if [ "$FREE" -lt 2 ]; then bad "Only ${FREE} GB free of ${TOTAL} GB - use Free Up Space"
else ok "${FREE} GB free of ${TOTAL} GB"; fi
[ "$TOTAL" -lt 32 ] && warn "Small drive (${TOTAL} GB) - it will fill up over time; 64 GB+ recommended"
[ "$(gsettings get org.gnome.software download-updates 2> /dev/null)" = "false" ] && ok "No automatic update downloads" || warn "Fedora downloads updates in the background (fills small drives)"
[ -f /etc/systemd/journald.conf.d/10-size-cap.conf ] && ok "System logs capped" || warn "System logs not capped (Free Up Space sets this)"

section "Kiosk"
command -v chromium-browser > /dev/null && ok "Chromium installed" || bad "Chromium not installed"
[ -f "$HOME/.config/autostart/suit-kiosk.desktop" ] && ok "Kiosk starts at login" || warn "Kiosk not set to start at login"
ls -d "$HOME"/.config/chromium/*/Extensions/oolfddhehmbpdnlmoljmllcdggmkgihh > /dev/null 2>&1 && ok "Tools for Autodarts installed" || warn "Tools for Autodarts not installed"
if [ -f "$HOME/.suit_rotation_config.json" ]; then
  echo "      screen: $(python3 -c 'import json; c=json.load(open("'"$HOME"'/.suit_rotation_config.json")); print("; ".join(f"{k} rotation {v.get("rotation")}, touch {v.get("touch_device")}" for k,v in c.items()))')"
fi

section "Remote support"
if command -v tailscale > /dev/null; then
  TS=$(tailscale status --json 2> /dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("BackendState",""), d.get("Self",{}).get("HostName",""), (d.get("TailscaleIPs") or [""])[0])' 2> /dev/null)
  [ "${TS%% *}" = "Running" ] && ok "Tailscale connected: ${TS#* }" || bad "Tailscale installed but not connected"
else
  bad "Tailscale not installed - no remote support possible"
fi
if grdctl status 2> /dev/null | grep -A3 -i "^RDP" | grep -qi "enabled"; then ok "Remote Desktop (RDP) on"; else warn "Remote Desktop (RDP) not enabled"; fi

echo
echo "RESULT: $PASS ok, $WARN warning(s), $FAIL problem(s)"
[ "$FAIL" -eq 0 ] && echo "Ready to ship once any warnings are understood." || echo "Fix the ✘ items before shipping."
} 2>&1 | tee "$REPORT"
echo "(report saved: $REPORT)"
