from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from send2trash import send2trash

from .models import OperationAction, PlannedOperation, PlanStatus


class OperationError(RuntimeError):
    pass


def _safe_move(source: Path, destination: Path) -> None:
    if not source.exists():
        raise OperationError(f"Source no longer exists: {source}")
    if destination.exists():
        raise OperationError(f"Destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def _safe_delete_to_trash(source: Path) -> None:
    if not source.exists():
        raise OperationError(f"Source no longer exists: {source}")
    send2trash(str(source))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _prune_empty_source_directories(
    sources: list[Path],
    cleanup_roots: list[Path] | None,
) -> list[str]:
    """Remove only empty source directories, never the user-selected root itself."""
    if not cleanup_roots:
        return []

    roots = [root.resolve() for root in cleanup_roots if root.exists()]
    candidates: set[Path] = set()

    for source in sources:
        current = source.parent
        while True:
            try:
                resolved = current.resolve()
            except OSError:
                resolved = current

            containing_roots = [root for root in roots if _is_relative_to(resolved, root)]
            if not containing_roots:
                break
            if any(resolved == root for root in containing_roots):
                break

            candidates.add(current)
            parent = current.parent
            if parent == current:
                break
            current = parent

    removed: list[str] = []
    for directory in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
            removed.append(str(directory))
        except (OSError, FileNotFoundError):
            pass
    return removed


def apply_plan(
    operations: list[PlannedOperation],
    log_dir: Path,
    cleanup_roots: list[Path] | None = None,
) -> Path:
    ready = [op for op in operations if op.status == PlanStatus.READY]
    if not ready:
        raise OperationError("There are no READY operations to apply.")

    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"apply-{timestamp}.json"

    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "state": "started",
        "operations": [
            {
                "source": str(op.source),
                "destination": str(op.destination) if op.destination is not None else None,
                "kind": op.kind.value,
                "action": op.action.value,
                "is_primary": op.is_primary,
                "applied": False,
            }
            for op in ready
        ],
    }
    log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    applied_sources: list[Path] = []
    try:
        for idx, op in enumerate(ready):
            if op.action == OperationAction.DELETE:
                _safe_delete_to_trash(op.source)
            else:
                if op.destination is None:
                    raise OperationError(f"Move operation has no destination: {op.source}")
                _safe_move(op.source, op.destination)

            applied_sources.append(op.source)
            record["operations"][idx]["applied"] = True
            log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    except Exception as exc:
        record["state"] = "partial_failure"
        record["error"] = str(exc)
        record["removed_empty_directories"] = _prune_empty_source_directories(
            applied_sources, cleanup_roots
        )
        log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        raise

    record["removed_empty_directories"] = _prune_empty_source_directories(
        applied_sources, cleanup_roots
    )
    record["state"] = "complete"
    record["completed_utc"] = datetime.now(timezone.utc).isoformat()
    log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return log_path


def undo_log(log_path: Path) -> tuple[int, list[str]]:
    if not log_path.exists():
        raise OperationError(f"Undo log not found: {log_path}")

    record = json.loads(log_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    undone = 0

    for entry in reversed(record.get("operations", [])):
        if not entry.get("applied"):
            continue

        action = entry.get("action", OperationAction.MOVE.value)
        if action == OperationAction.DELETE.value:
            errors.append(
                f"{entry.get('source')}: deleted leftovers were sent to the operating system "
                "Recycle Bin/Trash and must be restored from there."
            )
            continue

        original = Path(entry["source"])
        destination_value = entry.get("destination")
        if not destination_value:
            errors.append(f"Missing destination in undo log for: {original}")
            continue
        current = Path(destination_value)

        if not current.exists():
            errors.append(f"Missing current file: {current}")
            continue
        if original.exists():
            errors.append(f"Original path is occupied: {original}")
            continue

        try:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(original))
            entry["applied"] = False
            undone += 1
        except Exception as exc:
            errors.append(f"{current}: {exc}")

    record["state"] = "undone" if not errors else "undo_partial"
    record["undo_utc"] = datetime.now(timezone.utc).isoformat()
    record["undo_errors"] = errors
    log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    return undone, errors


def latest_completed_log(log_dir: Path) -> Path | None:
    if not log_dir.exists():
        return None

    candidates = sorted(log_dir.glob("apply-*.json"), reverse=True)
    for path in candidates:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if record.get("state") == "complete":
            return path
    return None
