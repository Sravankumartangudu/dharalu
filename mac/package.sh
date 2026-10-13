#!/bin/bash
# Packages WheatWise into dist/WheatWise-<version>.dmg, a drag-to-Applications installer.
set -euo pipefail
cd "$(dirname "$0")"

./build.sh --universal
VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" WheatWise.app/Contents/Info.plist)
DMG="dist/WheatWise-$VERSION.dmg"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

cp -R WheatWise.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/Read Me First.txt" <<'TXT'
Installing WheatWise for Mac

1. Drag WheatWise onto the Applications folder.
2. Open WheatWise from Applications. It isn't notarized by Apple, so the first time macOS
   says it can't be verified: go to System Settings > Privacy & Security, scroll down,
   click "Open Anyway", and confirm. You only need to do this once.
3. Allow notifications when asked - that is how it tells you when the BUY/SELL call changes.
4. WheatWise lives in the menu bar (🌾 SELL ₹2,590). Click it for today's call, the proof
   behind it, the track record and the briefing. "Open Dashboard…" opens the full site.
5. (Optional) Settings > Launch at Login, so it is always watching.

Full guide: https://github.com/Sravankumartangudu/wheatwise/blob/main/guide/MAC_APP.md
TXT

mkdir -p dist
rm -f "$DMG"
hdiutil create -quiet -volname "WheatWise" -srcfolder "$STAGE" -fs HFS+ -format UDZO "$DMG"
echo "Packaged $(pwd)/$DMG"
