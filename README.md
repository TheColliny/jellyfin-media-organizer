<div align="center">

<img src="jellyfin_organizer/assets/JellyfinMediaOrganizer-256.png" width="160" alt="Jellyfin Media Organizer">

# Jellyfin Media Organizer

**Rename and sort your movies and TV shows into a layout Jellyfin understands — with a preview before anything moves, and an undo after.**

[![Release](https://img.shields.io/github/v/release/TheColliny/jellyfin-media-organizer?label=release)](https://github.com/TheColliny/jellyfin-media-organizer/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

</div>

---

## Quick start

1. **Download** the installer for your system from the
   [latest release](https://github.com/TheColliny/jellyfin-media-organizer/releases/latest):

   | System | File |
   | --- | --- |
   | Windows 10/11 (64-bit) | `JellyfinMediaOrganizer-Setup-<version>.exe` |
   | macOS (Apple Silicon) | `JellyfinMediaOrganizer-<version>-macos-arm64.pkg` |
   | Debian / Ubuntu (amd64) | `jellyfin-media-organizer_<version>_amd64.deb` |

   No Python needed — the installers are self-contained.

2. **Install and launch it.** Windows: run the Setup EXE, then open *Jellyfin
   Media Organizer* from the Start menu. macOS: open the PKG (it is unsigned, so
   right-click → Open, or allow it in *System Settings → Privacy & Security*).
   Debian/Ubuntu: `sudo apt install ./jellyfin-media-organizer_<version>_amd64.deb`.

3. **Add a source folder** — the messy folder your downloads land in. The first
   folder you add also becomes the default output root; change it if you want the
   organized library somewhere else.

4. **Press Scan.** Nothing has moved yet. You get a queue of proposed operations,
   each marked **READY**, **REVIEW**, **SKIP**, or **ERROR**. Read it. Select rows
   you don't want and remove them from the queue — that only drops them from the
   plan, it never touches files on disk.

5. **Press Apply** to perform the remaining operations, and **Undo** if you change
   your mind — completed moves are logged so they can be reversed.

That's the whole loop: *scan → review → apply*. Everything below is optional.

## What you get

Given input like `The.Expanse.S02E05.1080p.WEB-DL.mkv` and
`Arrival 2016 REMUX.mkv`, the planner proposes:

```
Shows/
  The Expanse/
    Season 02/
      The Expanse S02E05.mkv
Movies/
  Arrival (2016)/
    Arrival (2016).mkv
```

- **Movies and TV are detected separately**, from `S01E02`, `1x02`, and
  multi-episode `S01E02-E03` patterns, with release-name noise (codecs,
  resolutions, group tags) stripped out of titles.
- **Sidecars follow their video** — subtitles (`.srt`, `.ass`, `.vtt`, …),
  artwork, `.nfo`, and external audio tracks that share the filename stem are
  renamed and moved alongside it, never on their own.
- **Extras are recognized**, not mangled: `trailers`, `featurettes`,
  `behind the scenes`, `deleted scenes`, samples, and similar folders/filenames.
- **Low-confidence guesses are never applied.** Anything ambiguous is marked
  REVIEW and left for you to decide.
- **Existing destinations are never overwritten.**
- **Leftover files are your call** — leave them untouched (default), move
  unambiguously associated ones along with the media, or send them to the
  Recycle Bin/Trash. Ambiguous leftovers are always left alone.
- **Optional folder monitoring** — a separate lightweight background process can
  watch folders recursively, wait for a new file to finish copying, and organize
  it automatically. It can start at login on Windows, macOS, and Linux.
- **In-app update check** tells you when a newer release is published and can
  download the right installer for your platform.

Supported video containers: `.mkv .mp4 .m4v .avi .mov .webm .wmv .mpg .mpeg .ts .m2ts .mts`

## Run from source

Needed on Intel Macs and other platforms without a prebuilt package. Requires
**Python 3.10+**.

```bash
git clone https://github.com/TheColliny/jellyfin-media-organizer.git
cd jellyfin-media-organizer
python run.py
```

`run.py` creates a private `.venv`, installs [PySide6](https://pypi.org/project/PySide6/)
and [Send2Trash](https://pypi.org/project/Send2Trash/) into it on first launch,
and starts the GUI. On Windows you can double-click
`START_JELLYFIN_ORGANIZER.bat` instead; on Linux/macOS, `./start_jellyfin_organizer.sh`.

To install it as a normal package instead:

```bash
python -m pip install -e .
jellyfin-organizer
```

Run the tests with `python -m pytest tests/ -q`.

## Build the installers yourself

Each script builds on its own platform, produces both the app and the background
monitor, and drops the finished package in `release/`.

| Platform | Script | Also needs |
| --- | --- | --- |
| Windows | `BUILD_WINDOWS_INSTALLER.bat` | [Inno Setup 6+](https://jrsoftware.org/isdl.php) |
| Windows (plain EXE, no installer) | `BUILD_WINDOWS_EXE.bat` | — |
| macOS | `./BUILD_MACOS_PKG.sh` | Xcode command line tools |
| Debian/Ubuntu | `./BUILD_LINUX_DEB.sh` | `dpkg-deb` |

CI does the same thing for every release — see
[`.github/workflows/release.yml`](.github/workflows/release.yml). Pushing a tag
like `v0.4.0` builds all three packages and publishes them as a GitHub Release.

## Where settings live

Monitor settings and activity logs are stored in the current user's application
config directory (`%APPDATA%` on Windows, `~/Library/Application Support` on
macOS, `~/.config` on Linux) — never inside the install directory, so upgrades
and uninstalls leave them alone.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Support

Bugs and feature requests: [open an issue](https://github.com/TheColliny/jellyfin-media-organizer/issues).

If this saved you an evening of renaming files, you can
[buy me a coffee](https://buymeacoffee.com/thecolliny). ☕

## License

[GNU General Public License v3.0 or later](LICENSE).

This program is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

Jellyfin Media Organizer is an independent project and is not affiliated with or
endorsed by the Jellyfin project.
