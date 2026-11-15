#!/bin/bash
# Build the Missions viewer: ~/Applications/Missions.app (main.swift in a window). Quit it first; the script refuses
# while it runs. --out <path.app> makes a test build there instead. Nothing is deleted: built in a temp folder, the old
# app is moved aside to another temp folder. Requires Xcode CLT (swiftc).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Missions.app"; BUNDLE_ID=com.ramosquant.missions.viewer; RUN=Missions
if [ "${1:-}" = --out ]; then
  [ $# -eq 2 ] && [[ "$2" == *.app ]] || { echo "usage: build_app.sh [--out <path.app>]" >&2; exit 2; }
  [ -d "$(dirname "$2")" ] || { echo "the --out folder does not exist" >&2; exit 2; }
  APP="$(cd "$(dirname "$2")" && pwd -P)/$(basename "$2")"; BUNDLE_ID="$BUNDLE_ID.test"
  [ "$APP" = "$HOME/Applications/Missions.app" ] && BUNDLE_ID=com.ramosquant.missions.viewer
elif [ $# -gt 0 ]; then echo "usage: build_app.sh [--out <path.app>]" >&2; exit 2; fi
guard() { if [ "$APP" = "$HOME/Applications/Missions.app" ] && pgrep -x "$RUN" >/dev/null; then
  echo "Missions is running: quit it first (nothing was changed)." >&2; exit 1; fi; }
guard
BUILD="$(mktemp -d)/Missions.app"
mkdir -p "$BUILD/Contents/MacOS" "$BUILD/Contents/Resources"
cat > "$BUILD/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Missions</string>
  <key>CFBundleDisplayName</key><string>Missions</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleExecutable</key><string>$RUN</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleIconFile</key><string>Missions</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Missions listens when you press the mic to dictate.</string>
  <key>NSSpeechRecognitionUsageDescription</key><string>Missions turns your dictation into text.</string>
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict>
</plist>
PLIST
cp "$HERE/Missions.icns" "$BUILD/Contents/Resources/Missions.icns"
swiftc -O "$HERE/main.swift" -o "$BUILD/Contents/MacOS/$RUN" -framework Cocoa -framework WebKit
codesign -s - --force --deep "$BUILD"
guard   # it may have been started during the build
mkdir -p "$(dirname "$APP")"
OLD=""
if [ -e "$APP" ]; then OLD="$(mktemp -d)/previous.app"; mv "$APP" "$OLD"; fi
if ! mv "$BUILD" "$APP"; then
  [ -n "$OLD" ] && mv "$OLD" "$APP"
  echo "could not install the new app; the previous one was put back" >&2; exit 1
fi
echo "built: $APP"
