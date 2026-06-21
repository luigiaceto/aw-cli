#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="AwWeb"
BUILD_DIR="$ROOT_DIR/macos/build"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
DMG_STAGING="$BUILD_DIR/dmg"
DMG_PATH="$ROOT_DIR/dist/$APP_NAME.dmg"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$BUILD_DIR/pycache}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$BUILD_DIR/pyinstaller-config}"

if [ -d /Applications/Xcode.app/Contents/Developer ] && xcode-select -p | grep -q "CommandLineTools"; then
  export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
fi

command -v xcrun >/dev/null 2>&1 || {
  echo "Errore: Xcode non trovato. Installa Xcode e aprilo almeno una volta." >&2
  exit 1
}

command -v uv >/dev/null 2>&1 || {
  echo "Errore: uv non trovato. Installa uv per costruire il backend Python." >&2
  exit 1
}

command -v hdiutil >/dev/null 2>&1 || {
  echo "Errore: hdiutil non trovato. Serve macOS per creare il DMG." >&2
  exit 1
}

cd "$ROOT_DIR"

echo "==> Pulizia build macOS"
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources" "$ROOT_DIR/dist"

echo "==> Build backend Python con PyInstaller"
uv run --with pyinstaller pyinstaller --clean --noconfirm packaging/aw-web-backend.spec

echo "==> Build wrapper Swift WKWebView"
xcrun swiftc \
  "$ROOT_DIR/macos/AwWeb/Sources/AwWebApp.swift" \
  -O \
  -module-cache-path "$BUILD_DIR/swift-module-cache" \
  -framework Cocoa \
  -framework WebKit \
  -o "$APP_DIR/Contents/MacOS/$APP_NAME"

echo "==> Assemblaggio app bundle"
cp "$ROOT_DIR/macos/AwWeb/Resources/Info.plist" "$APP_DIR/Contents/Info.plist"
cp -R "$ROOT_DIR/dist/aw-web-backend" "$APP_DIR/Contents/Resources/backend"
chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"
chmod +x "$APP_DIR/Contents/Resources/backend/aw-web-backend"

echo "==> Creazione DMG"
rm -rf "$DMG_STAGING" "$DMG_PATH"
mkdir -p "$DMG_STAGING"
cp -R "$APP_DIR" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo
echo "DMG creato: $DMG_PATH"
