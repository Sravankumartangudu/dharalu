#!/usr/bin/env bash
# Install / remove the launchd job that runs scripts/mac-refresh.sh every 5 minutes
# (and once when you log in). If the Mac is asleep, launchd runs it when it wakes.
#   scripts/mac-schedule.sh install | uninstall | status | run
set -euo pipefail
LABEL="com.sravankumartangudu.dharalu.refresh"
OLD_LABEL="com.sravankumartangudu.wheatwise.refresh"   # WheatWise 1.x (twice a day)
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/Library/Logs/Dharalu/refresh.log"
EVERY=300

remove_old() {
  launchctl bootout "gui/$(id -u)/$OLD_LABEL" 2>/dev/null || true
  if [ -f "$HOME/Library/LaunchAgents/$OLD_LABEL.plist" ]; then
    mv "$HOME/Library/LaunchAgents/$OLD_LABEL.plist" "$HOME/.Trash/" 2>/dev/null || rm -f "$HOME/Library/LaunchAgents/$OLD_LABEL.plist"
    echo "Removed the old WheatWise twice-a-day job"
  fi
}

case "${1:-status}" in
  install)
    remove_old
    mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO/scripts/mac-refresh.sh</string></array>
  <key>StartInterval</key><integer>$EVERY</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "Installed: checks every $((EVERY / 60)) minutes. Log: $LOG" ;;
  uninstall)
    remove_old
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"; echo "Removed" ;;
  run)
    launchctl kickstart "gui/$(id -u)/$LABEL" && echo "Started - see $LOG" ;;
  status)
    if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then echo "Installed (every $((EVERY / 60)) min). Last lines of $LOG:"; tail -8 "$LOG" 2>/dev/null
    else echo "Not installed - run: scripts/mac-schedule.sh install"; fi ;;
  *) echo "usage: $0 install | uninstall | status | run"; exit 2 ;;
esac
