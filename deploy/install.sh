#!/bin/bash
# Install Missions as an always-on launchd service on THIS Mac. Idempotent: re-running updates and restarts.
#   ./deploy/install.sh          install/refresh, then open http://127.0.0.1:8860
#   ./deploy/install.sh remove   unload and delete it
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LABEL=com.ramosquant.missions
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed"
  exit 0
fi

[ -x "$REPO/.venv/bin/python" ] || {
  python3 -m venv "$REPO/.venv"
  "$REPO/.venv/bin/pip" install -q -r "$REPO/requirements.txt"
}
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.missions"
sed -e "s|__REPO__|$REPO|g" -e "s|__HOME__|$HOME|g" "$REPO/deploy/com.ramosquant.missions.plist.template" > "$PLIST"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed: http://127.0.0.1:8860"
