# Session state — Jellyfin Media Organizer

Last updated: 2026-09-30

## Current goal

**0.4.0 is published.** https://github.com/TheColliny/jellyfin-media-organizer/releases/tag/v0.4.0
carries all three installers and release notes taken from CHANGELOG.md. The
whole pipeline — tag push → three platform builds → published release — has run
end to end successfully. Nothing is pending; the next work block starts on
whatever comes after 0.4.0.

## Where things stand

- Repo: https://github.com/TheColliny/jellyfin-media-organizer — public,
  default branch `main`, GPL-3.0-or-later, 2 commits.
- Version is single-sourced from `jellyfin_organizer/__init__.py`
  (`__version__ = "0.4.0"`). `pyproject.toml` restates it; the release workflow
  refuses a tag that disagrees with `__version__`.
- `CHANGELOG.md` holds all release notes (0.2.0 → 0.4.0). The per-version
  `RELEASE_NOTES_*.txt` files were deleted after being merged into it.
- `.github/workflows/release.yml` — a `v*` tag push (or manual dispatch) builds
  the Windows Setup EXE, macOS arm64 PKG and Debian amd64 DEB, then publishes a
  Release with those assets. On manual dispatch the publish job is skipped and
  the packages are uploaded as workflow artifacts only.
- `.github/workflows/ci.yml` — parser/planner tests on Linux/Windows/macOS for
  Python 3.10 and 3.12, plus a `pip install -e .` packaging check.
- Both workflows verified green. Two manual dry runs plus the real `v0.4.0` tag
  run all succeeded. Published assets: `JellyfinMediaOrganizer-Setup-0.4.0.exe`
  (177.9 MB), `jellyfin-media-organizer_0.4.0_amd64.deb` (82.1 MB),
  `JellyfinMediaOrganizer-0.4.0-macos-arm64.pkg` (50.1 MB).
- `_release_asset_for_platform` was replayed against the real release JSON: it
  resolves to the Setup EXE on win32, the arm64 PKG on darwin, and the DEB on
  linux. The in-app updater works against the live release.
- Commit identity for this repo is local-only:
  `TheColliny <83572066+TheColliny@users.noreply.github.com>` — the noreply
  address, so the real email stays out of a public history.
- Local git needed `http.version HTTP/1.1` and a large `http.postBuffer` to
  push at all; without them the push dies with "Connection was reset".

## Key decisions

- macOS ships **Apple Silicon only**. One `.pkg` per release keeps the in-app
  updater's asset matching unambiguous. Adding an x86_64 PKG would require
  teaching `_release_asset_for_platform` in `app.py` to prefer the running
  architecture first — do that change *before* shipping a second macOS asset.
- CI does not reuse `BUILD_WINDOWS_*.bat` (they `pause` and open browser pages
  on failure); the workflow repeats the PyInstaller/ISCC steps instead. The
  macOS and Linux shell scripts *are* reused and take `JMO_VERSION` from CI.
- No per-file GPL headers — `LICENSE` plus the README notice only.
- `.gitattributes` forces LF for `*.sh` and CRLF for `*.bat`/`*.iss`; the three
  shell scripts are committed mode 100755 so the runners can execute them.

## Open items

1. Releasing a future version is: bump `__version__` in
   `jellyfin_organizer/__init__.py` and `version` in `pyproject.toml`, add a
   `## X.Y.Z` section to `CHANGELOG.md`, then `git tag vX.Y.Z && git push
   origin vX.Y.Z`. Mismatched tag/version fails the `prepare` job by design.
   If the publish job ever fails, the build artifacts survive on the run — fix
   forward and re-run the failed job on that same run; do not delete the tag.
2. Windows installer is 178 MB because the Windows build passes
   `--collect-all PySide6`. Trimming unused Qt modules is a later follow-up;
   the Linux and macOS packages do not use that flag.
3. macOS PKG is unsigned/unnotarized. Public distribution would want an Apple
   Developer ID plus notarization; users currently need right-click → Open.
