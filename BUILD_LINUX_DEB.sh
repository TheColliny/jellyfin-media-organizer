#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${JMO_VERSION:-0.4.0}"
PKGROOT="build/debroot"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required on the build computer."
  exit 1
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb is required to build the Debian/Ubuntu installer package."
  exit 1
fi

rm -rf .build-venv build dist "$PKGROOT"
python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . pyinstaller

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name JellyfinMediaOrganizer \
  --icon "jellyfin_organizer/assets/JellyfinMediaOrganizer.png" \
  --add-data "jellyfin_organizer/assets:jellyfin_organizer/assets" \
  windows_entry.py

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name JellyfinMediaMonitor \
  monitor_entry.py

mkdir -p "$PKGROOT/DEBIAN" \
         "$PKGROOT/opt/jellyfin-media-organizer" \
         "$PKGROOT/opt/jellyfin-media-organizer/monitor" \
         "$PKGROOT/usr/share/applications" \
         "$PKGROOT/usr/share/icons/hicolor/256x256/apps"
cp -a dist/JellyfinMediaOrganizer/. "$PKGROOT/opt/jellyfin-media-organizer/"
cp -a dist/JellyfinMediaMonitor/. "$PKGROOT/opt/jellyfin-media-organizer/monitor/"
cp installer/linux/jellyfin-media-organizer.desktop "$PKGROOT/usr/share/applications/"
cp jellyfin_organizer/assets/JellyfinMediaOrganizer-256.png \
  "$PKGROOT/usr/share/icons/hicolor/256x256/apps/jellyfin-media-organizer.png"
cat > "$PKGROOT/DEBIAN/control" <<CONTROL
Package: jellyfin-media-organizer
Version: $VERSION
Section: video
Priority: optional
Architecture: $ARCH
Maintainer: Jellyfin Media Organizer
Description: GUI utility for organizing media into Jellyfin-friendly folders and filenames.
CONTROL

mkdir -p release
dpkg-deb --build "$PKGROOT" "release/jellyfin-media-organizer_${VERSION}_${ARCH}.deb"
echo
echo "Built: release/jellyfin-media-organizer_${VERSION}_${ARCH}.deb"
echo "The DEB includes the lightweight background monitor under /opt/jellyfin-media-organizer/monitor."
