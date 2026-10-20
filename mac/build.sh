#!/bin/bash
# Builds Dharalu.app next to this script. Pass --universal for an Apple Silicon + Intel build.
set -euo pipefail
cd "$(dirname "$0")"

APP="Dharalu.app"
VERSION="2.2.0"
ARCHS="$(uname -m)"
[[ "${1:-}" == "--universal" ]] && ARCHS="arm64 x86_64"

# Regenerate the icon if it's missing.
[[ -f Icon/AppIcon.icns ]] || swift Icon/make_icon.swift

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

SRC="main.swift NexusBeacon.swift"
BINS=()
for arch in $ARCHS; do
  swiftc -O -target "$arch-apple-macos13.0" \
    -framework AppKit -framework WebKit -framework ServiceManagement -framework UserNotifications \
    $SRC -o "$APP/Contents/MacOS/Dharalu-$arch"
  BINS+=("$APP/Contents/MacOS/Dharalu-$arch")
done
lipo -create "${BINS[@]}" -output "$APP/Contents/MacOS/Dharalu"
rm "${BINS[@]}"

cp Icon/AppIcon.icns "$APP/Contents/Resources/"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Dharalu</string>
  <key>CFBundleDisplayName</key><string>Dharalu</string>
  <key>CFBundleIdentifier</key><string>com.sravankumartangudu.dharalu</string>
  <key>CFBundleExecutable</key><string>Dharalu</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSUIElement</key><true/>
  <key>NSHumanReadableCopyright</key><string>MIT licence · github.com/Sravankumartangudu/dharalu</string>
</dict>
</plist>
PLIST

# Ad-hoc sign so the notification permission sticks to a stable identity.
codesign --force --sign - "$APP" >/dev/null
echo "Built $APP $VERSION"
