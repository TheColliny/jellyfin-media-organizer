# Changelog

All notable changes to Jellyfin Media Organizer are documented here, newest first.

Across every release the core safety behavior is unchanged: the app previews
every operation before touching anything, never blindly overwrites an existing
destination, and logs completed operations so they can be undone.

---

## 0.4.0

### Artwork / header polish
- Removed the white exterior corners from the jellyfish artwork using alpha transparency.
- Regenerated PNG, Windows ICO, and macOS ICNS assets with transparent corners.
- The in-app jellyfish logo now has a subtle runtime drop shadow against the blue header.
- Added Buy Me a Coffee artwork beneath the version badge, linking to https://buymeacoffee.com/thecolliny.
- The coffee artwork is scaled to the version-badge width and has a transparent exterior.

### Update checking
- Added a "Check for updates" link at the bottom-right of the application header.
- Checks the latest published release of `TheColliny/jellyfin-media-organizer` on GitHub.
- Compares the GitHub release tag with the installed application version.
- Newer versions offer "Download" and "Maybe later".
- Downloads the platform-appropriate release asset into the user's Downloads folder.
- After a successful download, the user can open the installer/package directly.
- If a release has no suitable installer asset, the release page is opened instead.
- Network/update work runs off the GUI thread.

### Windows upgrade behavior
- Keeps the same permanent Inno Setup AppId, so new installers recognize the existing installation.
- Explicitly reuses the prior install location and selected installer tasks.
- New versions overwrite/update application files in place; no full uninstall is required.
- Setup stops `JellyfinMediaMonitor.exe` before copying new files so the monitor can be replaced cleanly.
- Added publisher/support/update URLs to Windows Installed Apps metadata.

### Release packaging note
Each GitHub Release should carry the generated Windows installer, preferably named
`JellyfinMediaOrganizer-Setup-X.Y.Z.exe` — the in-app updater prefers that
Setup/Installer EXE on Windows. The release workflow in
`.github/workflows/release.yml` produces exactly that name.

---

## 0.3.0

### Queue and path display
- Source and Destination columns show paths relative to the selected input/output roots instead of collapsing to `C:...`.
- Selecting one queue row shows the complete absolute source and destination paths underneath the table.
- Source, Destination, and Reason columns are manually resizable, and the table supports horizontal scrolling.
- Queue rows support native multi-selection (Shift and Ctrl on Windows/Linux; Shift and Command on macOS).
- "Remove Selected from Queue" plus Delete/Backspace removes items from the pending plan without touching files on disk.
- Removing a primary media row also removes its directly attached sidecar actions, so subtitles/artwork are never moved alone.

### Output root
- The first input folder automatically becomes the default output root.
- A manually chosen output root remains unchanged as more input folders are added.

### Leftover-file policy
- Leave leftovers untouched (default).
- Move unambiguously associated leftover files alongside the organized media.
- Delete unambiguously associated leftovers by sending them to the OS Recycle Bin/Trash.
- Ambiguous leftovers are marked REVIEW and are never automatically moved or deleted.
- Empty source subfolders are removed after successful moves when safe to do so.

### Folder monitoring
- New Folder Monitoring dialog.
- Select one or more folders to watch recursively.
- Separate lightweight, GUI-free monitor executable/process.
- Waits until a new or changed video is stable before processing it.
- Low-confidence matches are skipped and logged rather than guessed.
- Optional start-at-login integration for Windows, macOS, and Linux.
- Monitor settings and activity logs are stored in the current user's application config directory.
- Windows/macOS/Linux package build scripts now include the background monitor.

### Windows installer
- Installer now includes `JellyfinMediaMonitor.exe` under the program installation directory.
- Uninstall attempts to stop the monitor and removes the per-user monitor startup value.

### Safety note
Files selected by the Delete-leftovers policy are sent to the operating system
Recycle Bin/Trash. Undo reverses move operations, but deleted leftovers must be
restored from the OS Trash if needed.

---

## 0.2.1

### Installer build fix
- Reworked the Inno Setup build to use an absolute project root supplied by `BUILD_WINDOWS_INSTALLER.bat` instead of depending on nested `..\..` paths.
- Added explicit preflight checks for the PyInstaller EXE, icon, and `.iss` file, so missing paths produce a useful message before Inno Setup is launched.
- Added build diagnostics showing the project root, application build path, and Inno Setup compiler being used.
- Expected Windows installer output: `release\JellyfinMediaOrganizer-Setup-0.2.1.exe`.

### GUI redesign
- Replaced the default grey Qt appearance with a custom aqua/blue visual theme derived from the application artwork.
- Added a branded header with the application icon, title, description, and version badge.
- Added rounded white content cards, blue/cyan controls, a green Apply button, a coral Undo button, and a matching progress bar.
- Improved the source-folder and preview layouts.
- Added source-folder count feedback.
- Added colored READY / REVIEW / SKIP / ERROR status cells in the preview.
- The same custom theme is used on Windows, Linux, and macOS through Qt Fusion plus a stylesheet.

---

## 0.2.0

### Packaging / installation
- Added a real Windows installer build using Inno Setup.
- Installs under `Program Files\Jellyfin Media Organizer`.
- Registers a Start-menu application entry.
- Registers an uninstall entry in Windows Installed Apps / Add or Remove Programs.
- Adds an optional desktop-shortcut installer task.
- End users of the finished Setup EXE do not need Python.
- Windows build scripts direct the developer to the official Python download page if Python 3.10+ is missing.
- Windows installer builder directs the developer to Inno Setup if its compiler is missing.

### Branding
- Added the Jellyfin Media Organizer artwork as PNG, Windows ICO, and macOS ICNS resources.
- Windows executable and installer now use the program icon.
- The Qt application sets the icon for application/window/taskbar integration.
- Added a stable Windows AppUserModelID for shortcut/taskbar grouping.

### Other platforms
- Added a macOS PKG build script that installs the app into `/Applications`.
- Added a Debian/Ubuntu DEB build script with an `/opt` install and desktop-menu registration.
