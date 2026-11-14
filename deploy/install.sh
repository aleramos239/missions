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

if [ ! -x "$REPO/.venv/bin/python" ]; then
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo "Python 3.11 or newer is needed (python3 is older)" >&2; exit 1; }
  python3 -m venv "$REPO/.venv"
fi
# always: a re-run repairs a half-installed venv and picks up new requirements
"$REPO/.venv/bin/pip" install -q -r "$REPO/requirements.txt"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.missions"
"$REPO/.venv/bin/python" "$REPO/deploy/fill.py" "$REPO/deploy/com.ramosquant.missions.plist.template" "$PLIST" "$REPO" "$HOME"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
for _ in $(seq 10); do  # bootout is asynchronous: wait until the job is gone
  launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break
  sleep 0.5
done
launchctl bootstrap "gui/$(id -u)" "$PLIST" || { sleep 2; launchctl bootstrap "gui/$(id -u)" "$PLIST"; }
echo "installed: http://127.0.0.1:8860"
