#!/usr/bin/env bash
# Install / remove the launchd job that runs scripts/mac-refresh.sh at 12:00 and 19:00 (your Mac's time).
# That's half an hour before each GitHub Actions run, so Actions re-publishes fresh prices.
# If the Mac is asleep at those times, launchd runs the job when it wakes.
#   scripts/mac-schedule.sh install | uninstall | status | run
set -euo pipefail
LABEL="com.sravankumartangudu.wheatwise.refresh"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/Library/Logs/WheatWise/refresh.log"

case "${1:-status}" in
  install)
    mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO/scripts/mac-refresh.sh</string></array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "Installed: refreshes at 12:00 and 19:00. Log: $LOG" ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"; echo "Removed" ;;
  run)
    launchctl kickstart "gui/$(id -u)/$LABEL" && echo "Started - see $LOG" ;;
  status)
    if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then echo "Installed. Last lines of $LOG:"; tail -5 "$LOG" 2>/dev/null
    else echo "Not installed - run: scripts/mac-schedule.sh install"; fi ;;
  *) echo "usage: $0 install | uninstall | status | run"; exit 2 ;;
esac
