from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

from .models import LeftoverPolicy, OperationAction, PlanStatus
from .monitor_config import (
    heartbeat_path,
    load_monitor_settings,
    monitor_is_running,
    monitor_log_path,
)
from .operations import apply_plan
from .parser import is_video, parse_media
from .planner import build_plan


def _log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with monitor_log_path().open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def _heartbeat() -> None:
    payload = {"pid": os.getpid(), "updated": time.time()}
    try:
        heartbeat_path().write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass


def _ignored(path: Path) -> bool:
    return any(part.startswith(".jellyfin-organizer") for part in path.parts)


class DirectoryWatcher:
    """Low-overhead polling watcher.

    The monitor performs one recursive baseline walk when it starts, then polls
    directory modification times. Only directories whose contents changed are
    listed again. Candidate media files are stat'ed while waiting for them to
    become stable, avoiding a full recursive file scan every few seconds.
    """

    def __init__(self, roots: list[Path]):
        self.roots = roots
        self.dir_mtimes: dict[Path, int] = {}
        self.videos_by_dir: dict[Path, set[Path]] = {}
        for root in roots:
            if root.exists() and root.is_dir():
                self._discover_tree(root, report_videos=False)

    def _dir_mtime(self, directory: Path) -> int:
        try:
            return directory.stat().st_mtime_ns
        except OSError:
            return -1

    def _discover_tree(self, directory: Path, *, report_videos: bool) -> list[Path]:
        discovered: list[Path] = []
        stack = [directory]
        while stack:
            current = stack.pop()
            if _ignored(current) or not current.exists() or not current.is_dir():
                continue
            self.dir_mtimes[current] = self._dir_mtime(current)
            direct_videos: set[Path] = set()
            try:
                entries = list(current.iterdir())
            except OSError:
                entries = []
            for entry in entries:
                if _ignored(entry):
                    continue
                try:
                    if entry.is_dir():
                        stack.append(entry)
                    elif entry.is_file() and is_video(entry):
                        direct_videos.add(entry)
                        if report_videos:
                            discovered.append(entry)
                except OSError:
                    continue
            self.videos_by_dir[current] = direct_videos
        return discovered

    def poll_new_videos(self) -> list[Path]:
        new_videos: list[Path] = []
        for directory in list(self.dir_mtimes):
            if not directory.exists():
                self.dir_mtimes.pop(directory, None)
                self.videos_by_dir.pop(directory, None)
                continue

            current_mtime = self._dir_mtime(directory)
            if current_mtime == self.dir_mtimes.get(directory):
                continue
            self.dir_mtimes[directory] = current_mtime

            try:
                entries = list(directory.iterdir())
            except OSError:
                continue

            existing_dirs: set[Path] = set()
            direct_videos: set[Path] = set()
            for entry in entries:
                if _ignored(entry):
                    continue
                try:
                    if entry.is_dir():
                        existing_dirs.add(entry)
                        if entry not in self.dir_mtimes:
                            new_videos.extend(self._discover_tree(entry, report_videos=True))
                    elif entry.is_file() and is_video(entry):
                        direct_videos.add(entry)
                except OSError:
                    continue

            previous = self.videos_by_dir.get(directory, set())
            new_videos.extend(sorted(direct_videos - previous))
            self.videos_by_dir[directory] = direct_videos

            # Child directories removed from this parent will also be noticed in
            # the top-level loop, but remove their immediate records promptly.
            known_children = [
                child for child in self.dir_mtimes if child.parent == directory
            ]
            for child in known_children:
                if child not in existing_dirs:
                    self.dir_mtimes.pop(child, None)
                    self.videos_by_dir.pop(child, None)

        # Preserve order while removing duplicates (for example when a new tree
        # is discovered and its parent is also processed during the same poll).
        return list(dict.fromkeys(new_videos))

    def mark_known_video(self, path: Path) -> None:
        """Absorb a destination created by this monitor so it is not re-queued."""
        containing = [
            root
            for root in self.roots
            if _path_within(path, root)
        ]
        if not containing:
            return
        root = max(containing, key=lambda p: len(p.parts))
        current = path.parent
        chain: list[Path] = []
        while True:
            chain.append(current)
            if current == root or current.parent == current:
                break
            current = current.parent
        for directory in reversed(chain):
            if directory.exists():
                self.dir_mtimes[directory] = self._dir_mtime(directory)
                self.videos_by_dir.setdefault(directory, set())
        if path.exists() and is_video(path):
            self.videos_by_dir.setdefault(path.parent, set()).add(path)


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _containing_watch_root(path: Path, roots: list[Path]) -> Path | None:
    matches: list[Path] = []
    for root in roots:
        try:
            path.resolve().relative_to(root.resolve())
            matches.append(root)
        except (OSError, ValueError):
            continue
    if not matches:
        return None
    return max(matches, key=lambda p: len(p.parts))


def _process_file(path: Path, roots: list[Path], settings) -> list[Path]:
    if not path.exists():
        return []

    watch_root = _containing_watch_root(path, roots)
    if watch_root is None:
        return []

    output_root = Path(settings.output_root) if settings.output_root else watch_root
    output_root.mkdir(parents=True, exist_ok=True)

    item = parse_media(path)
    leftover_policy = LeftoverPolicy(settings.leftover_policy)
    if leftover_policy != LeftoverPolicy.LEAVE:
        # Automatic leftover handling is safe for a conventional single-video
        # movie folder. If the new file shares a source folder with other video
        # files, leave leftovers alone rather than risk assigning them wrongly.
        try:
            other_videos = [
                sibling
                for sibling in path.parent.iterdir()
                if sibling.is_file() and is_video(sibling) and sibling != path
            ]
        except OSError:
            other_videos = []
        if other_videos:
            _log(
                f"Leftover policy temporarily reduced to LEAVE for {path.parent} because the folder "
                "contains multiple video files and association would be ambiguous."
            )
            leftover_policy = LeftoverPolicy.LEAVE

    plan = build_plan(
        [item],
        output_root,
        leftover_policy=leftover_policy,
    )
    primary = next((op for op in plan if op.is_primary), None)
    if primary is None:
        return []

    if primary.status != PlanStatus.READY:
        _log(
            f"Skipped {path} ({primary.status.value}, confidence {primary.confidence:.0%}): "
            f"{primary.reason or 'manual review required'}"
        )
        return []

    ready = [op for op in plan if op.status == PlanStatus.READY]
    delete_count = sum(op.action == OperationAction.DELETE for op in ready)
    if delete_count:
        _log(
            f"Processing {path} with {delete_count} leftover file(s) configured for Recycle Bin/Trash."
        )

    log_dir = output_root / ".jellyfin-organizer-logs"
    apply_plan(plan, log_dir, cleanup_roots=roots)
    destinations = [op.destination for op in ready if op.destination is not None]
    _log(f"Organized {path} -> {primary.destination}")
    return destinations


def run_monitor() -> int:
    # Prevent an accidental duplicate monitor in the common case.
    if monitor_is_running(max_age_seconds=15):
        return 0

    settings = load_monitor_settings()
    if not settings.enabled:
        return 0

    roots = [Path(value) for value in settings.folders if value]
    watcher = DirectoryWatcher(roots)
    candidates: dict[Path, dict[str, object]] = {}
    last_folder_signature = tuple(sorted(str(p) for p in roots))
    _heartbeat()
    _log(
        f"Monitor started. Watching {len(roots)} folder(s); existing video files are treated as baseline."
    )

    try:
        while True:
            settings = load_monitor_settings()
            if not settings.enabled:
                _log("Monitor disabled in settings; exiting.")
                break

            roots = [Path(value) for value in settings.folders if value]
            folder_signature = tuple(sorted(str(p) for p in roots))
            if folder_signature != last_folder_signature:
                watcher = DirectoryWatcher(roots)
                candidates.clear()
                last_folder_signature = folder_signature
                _log(f"Watch-folder configuration changed; now watching {len(roots)} folder(s).")

            now = time.time()
            for path in watcher.poll_new_videos():
                if path not in candidates:
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    candidates[path] = {
                        "signature": (stat.st_size, stat.st_mtime_ns),
                        "changed_at": now,
                    }
                    _log(f"Detected new video: {path}")

            for path in list(candidates):
                state = candidates[path]
                if not path.exists():
                    candidates.pop(path, None)
                    continue
                try:
                    stat = path.stat()
                    signature = (stat.st_size, stat.st_mtime_ns)
                except OSError:
                    continue

                if state["signature"] != signature:
                    state["signature"] = signature
                    state["changed_at"] = now
                    continue

                stable_for = now - float(state["changed_at"])
                if stable_for < max(5, int(settings.stable_seconds)):
                    continue

                try:
                    destinations = _process_file(path, roots, settings)
                    for destination in destinations:
                        watcher.mark_known_video(destination)
                except Exception as exc:
                    _log(f"Error processing {path}: {exc}\n{traceback.format_exc()}")
                finally:
                    candidates.pop(path, None)

            _heartbeat()
            time.sleep(max(2, int(settings.poll_seconds)))
    finally:
        try:
            heartbeat_path().unlink(missing_ok=True)
        except Exception:
            pass
        _log("Monitor stopped.")
    return 0


def main() -> None:
    raise SystemExit(run_monitor())


if __name__ == "__main__":
    main()
