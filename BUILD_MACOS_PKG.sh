#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${JMO_VERSION:-0.4.0}"
VENV=".build-venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required on the build Mac."
  echo "Download it from: https://www.python.org/downloads/macos/"
  open "https://www.python.org/downloads/macos/" || true
  exit 1
fi
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || {
  echo "Python 3.10+ is required on the build Mac."
  open "https://www.python.org/downloads/macos/" || true
  exit 1
}

rm -rf "$VENV" build dist
python3 -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e . pyinstaller

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "Jellyfin Media Organizer" \
  --icon "jellyfin_organizer/assets/JellyfinMediaOrganizer.icns" \
  --add-data "jellyfin_organizer/assets:jellyfin_organizer/assets" \
  windows_entry.py

python -m PyInstaller \
  --noconfirm \
  --clean \
  --name "JellyfinMediaMonitor" \
  monitor_entry.py

MONITOR_DEST="dist/Jellyfin Media Organizer.app/Contents/Resources/monitor"
mkdir -p "$MONITOR_DEST"
cp -a dist/JellyfinMediaMonitor/. "$MONITOR_DEST/"

mkdir -p release
pkgbuild \
  --component "dist/Jellyfin Media Organizer.app" \
  --install-location "/Applications" \
  --identifier "org.jellyfinmediaorganizer.desktop" \
  --version "$VERSION" \
  "release/JellyfinMediaOrganizer-$VERSION.pkg"

echo
echo "Built: release/JellyfinMediaOrganizer-$VERSION.pkg"
echo "The PKG includes the lightweight background monitor inside the app bundle."
echo "This package is unsigned; public distribution should add Apple Developer ID signing and notarization."
