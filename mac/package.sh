#!/bin/bash
# Packages Dharalu into dist/Dharalu-<version>.dmg, a drag-to-Applications installer.
set -euo pipefail
cd "$(dirname "$0")"

./build.sh --universal
VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" Dharalu.app/Contents/Info.plist)
DMG="dist/Dharalu-$VERSION.dmg"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

cp -R Dharalu.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/Read Me First.txt" <<'TXT'
Installing Dharalu for Mac

1. Drag Dharalu onto the Applications folder.
2. Open Dharalu from Applications. It isn't notarized by Apple, so the first time macOS
   says it can't be verified: go to System Settings > Privacy & Security, scroll down,
   click "Open Anyway", and confirm. You only need to do this once.
3. Allow notifications when asked - that is how it tells you when a BUY/SELL call changes
   or a price jumps.
4. Dharalu lives in the menu bar (⚖️ 🌾 SELL ₹2,693). Click it for wheat, gold, silver and
   platinum - each has the proof, the track record and the briefing. Gold, silver and
   platinum are checked live every 5 minutes. "Open Dashboard…" opens the full site.
5. Settings > Menu bar > Show picks which one the menu bar shows.
6. (Optional) Settings > Launch at Login, so it is always watching.

Upgrading from WheatWise? Quit it and move WheatWise.app to the Bin - Dharalu replaces it.

Full guide: https://github.com/Sravankumartangudu/dharalu/blob/main/guide/MAC_APP.md
TXT

mkdir -p dist
rm -f "$DMG"
hdiutil create -quiet -volname "Dharalu" -srcfolder "$STAGE" -fs HFS+ -format UDZO "$DMG"
echo "Packaged $(pwd)/$DMG"
