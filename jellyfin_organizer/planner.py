from __future__ import annotations

import re
from pathlib import Path

from .models import (
    LeftoverPolicy,
    MediaKind,
    OperationAction,
    ParsedMedia,
    PlannedOperation,
    PlanStatus,
)
from .parser import SIDECAR_EXTENSIONS

INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def clean_component(name: str) -> str:
    cleaned = INVALID_CHARS.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned or "Unknown"


def media_label(item: ParsedMedia) -> str:
    title = clean_component(item.title)
    if item.year:
        return f"{title} ({item.year})"
    return title


def episode_code(item: ParsedMedia) -> str:
    assert item.season is not None and item.episode is not None
    base = f"S{item.season:02d}E{item.episode:02d}"
    if item.episode_end and item.episode_end != item.episode:
        base += f"-E{item.episode_end:02d}"
    return base


def _destination_for(item: ParsedMedia, output_root: Path) -> Path:
    label = media_label(item)
    ext = item.source.suffix.lower()

    if item.kind == MediaKind.TV:
        assert item.season is not None and item.episode is not None
        series_dir = output_root / "Shows" / label
        season_dir = series_dir / f"Season {item.season:02d}"
        filename = f"{label} {episode_code(item)}{ext}"
        return season_dir / filename

    movie_dir = output_root / "Movies" / label
    return movie_dir / f"{label}{ext}"


def _sidecar_destinations(
    item: ParsedMedia,
    primary_destination: Path,
) -> list[tuple[Path, Path]]:
    """Match conventional media sidecars that share the primary filename stem."""
    src = item.source
    stem = src.stem
    matches: list[tuple[Path, Path]] = []

    try:
        siblings = list(src.parent.iterdir())
    except OSError:
        return matches

    for sibling in siblings:
        if not sibling.is_file() or sibling == src:
            continue
        lower_name = sibling.name.lower()
        lower_stem = stem.lower()

        if not (
            lower_name == lower_stem + sibling.suffix.lower()
            or lower_name.startswith(lower_stem + ".")
        ):
            continue

        if sibling.suffix.lower() not in SIDECAR_EXTENSIONS:
            continue

        suffix_tail = sibling.name[len(stem):]
        dest_name = primary_destination.stem + suffix_tail
        matches.append((sibling, primary_destination.with_name(dest_name)))

    return matches


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _is_protected_output_path(path: Path, output_root: Path) -> bool:
    protected = (
        output_root / "Movies",
        output_root / "Shows",
        output_root / ".jellyfin-organizer-logs",
    )
    return any(_is_relative_to(path, base) for base in protected)


def _append_leftover_operations(
    operations: list[PlannedOperation],
    output_root: Path,
    policy: LeftoverPolicy,
    claimed_destinations: dict[Path, Path],
) -> None:
    if policy == LeftoverPolicy.LEAVE:
        return

    ready_primaries = [
        op
        for op in operations
        if op.is_primary
        and op.status == PlanStatus.READY
        and op.action == OperationAction.MOVE
        and op.destination is not None
    ]
    if not ready_primaries:
        return

    by_source_dir: dict[Path, list[PlannedOperation]] = {}
    all_primaries = [op for op in operations if op.is_primary and op.destination is not None]
    for op in all_primaries:
        by_source_dir.setdefault(op.source.parent, []).append(op)

    # A source directory is safe for automatic leftover handling only when every
    # primary media file in that directory is heading to the same destination
    # directory. This covers a normal single-movie folder and a TV season folder,
    # while avoiding destructive guesses in flat folders containing many movies.
    mapped_dirs: dict[Path, Path] = {}
    ambiguous_dirs: set[Path] = set()
    for source_dir, group in by_source_dir.items():
        destinations = {op.destination.parent for op in group if op.destination is not None}
        all_ready = all(op.status == PlanStatus.READY for op in group)
        if all_ready and len(destinations) == 1:
            mapped_dirs[source_dir] = next(iter(destinations))
        else:
            ambiguous_dirs.add(source_dir)

    planned_sources = {op.source for op in operations}
    emitted_sources: set[Path] = set()
    mapped_sorted = sorted(mapped_dirs, key=lambda p: len(p.parts), reverse=True)

    def nearest_mapping(path: Path) -> Path | None:
        for candidate in mapped_sorted:
            if _is_relative_to(path, candidate):
                return candidate
        return None

    for source_dir, dest_dir in mapped_dirs.items():
        try:
            candidates = list(source_dir.rglob("*"))
        except OSError:
            continue

        for source in candidates:
            if not source.is_file() or source in planned_sources or source in emitted_sources:
                continue
            if any(part.startswith(".jellyfin-organizer") for part in source.parts):
                continue
            if _is_protected_output_path(source, output_root):
                continue
            if nearest_mapping(source) != source_dir:
                continue

            emitted_sources.add(source)
            group_id = f"folder:{source_dir}"

            if policy == LeftoverPolicy.DELETE:
                operations.append(
                    PlannedOperation(
                        source=source,
                        destination=None,
                        kind=MediaKind.UNKNOWN,
                        confidence=1.0,
                        status=PlanStatus.READY,
                        action=OperationAction.DELETE,
                        reason="Associated leftover file — send to the operating system Recycle Bin/Trash.",
                        is_primary=False,
                        group_id=group_id,
                    )
                )
                continue

            try:
                relative = source.relative_to(source_dir)
            except ValueError:
                relative = Path(source.name)
            destination = dest_dir / relative
            status = PlanStatus.READY
            reason = "Associated leftover file — move with organized media."

            if destination.exists():
                status = PlanStatus.REVIEW
                reason = "Leftover destination already exists; overwrite is not allowed."
            prior = claimed_destinations.get(destination)
            if prior and prior != source:
                status = PlanStatus.REVIEW
                reason = f"Leftover destination collision with: {prior}"
            else:
                claimed_destinations[destination] = source

            operations.append(
                PlannedOperation(
                    source=source,
                    destination=destination,
                    kind=MediaKind.UNKNOWN,
                    confidence=1.0,
                    status=status,
                    action=OperationAction.MOVE,
                    reason=reason,
                    is_primary=False,
                    group_id=group_id,
                )
            )

    # Surface ambiguous direct leftovers instead of silently deleting/moving them.
    # REVIEW rows are never automatically applied.
    for source_dir in ambiguous_dirs:
        try:
            candidates = list(source_dir.iterdir())
        except OSError:
            continue
        for source in candidates:
            if not source.is_file() or source in planned_sources or source in emitted_sources:
                continue
            if _is_protected_output_path(source, output_root):
                continue
            operations.append(
                PlannedOperation(
                    source=source,
                    destination=None,
                    kind=MediaKind.UNKNOWN,
                    confidence=0.0,
                    status=PlanStatus.REVIEW,
                    action=(
                        OperationAction.DELETE
                        if policy == LeftoverPolicy.DELETE
                        else OperationAction.MOVE
                    ),
                    reason=(
                        "Leftover file is in a folder containing media headed to multiple destinations; "
                        "it was left untouched because its association is ambiguous."
                    ),
                    is_primary=False,
                    group_id=f"folder:{source_dir}",
                )
            )


def build_plan(
    items: list[ParsedMedia],
    output_root: Path,
    min_confidence: float = 0.80,
    leftover_policy: LeftoverPolicy | str = LeftoverPolicy.LEAVE,
) -> list[PlannedOperation]:
    if isinstance(leftover_policy, str):
        leftover_policy = LeftoverPolicy(leftover_policy)

    operations: list[PlannedOperation] = []
    claimed_destinations: dict[Path, Path] = {}

    for item in items:
        destination = _destination_for(item, output_root)
        status = PlanStatus.READY
        reason = ""
        group_id = str(item.source)

        if item.confidence < min_confidence:
            status = PlanStatus.REVIEW
            reason = "Parser confidence is below the safe threshold."

        if destination.exists():
            try:
                same = item.source.resolve() == destination.resolve()
            except OSError:
                same = item.source == destination

            if same:
                status = PlanStatus.SKIP
                reason = "Already Jellyfin-friendly."
            else:
                status = PlanStatus.REVIEW
                reason = "Destination already exists; overwrite is not allowed."

        prior = claimed_destinations.get(destination)
        if prior and prior != item.source:
            status = PlanStatus.REVIEW
            reason = f"Destination collision with: {prior}"
        else:
            claimed_destinations[destination] = item.source

        operations.append(
            PlannedOperation(
                source=item.source,
                destination=destination,
                kind=item.kind,
                confidence=item.confidence,
                status=status,
                action=OperationAction.MOVE,
                reason=reason or "; ".join(item.notes),
                is_primary=True,
                group_id=group_id,
            )
        )

        if status == PlanStatus.READY:
            for src_sidecar, dst_sidecar in _sidecar_destinations(item, destination):
                side_status = PlanStatus.READY
                side_reason = "Related sidecar file."
                if dst_sidecar.exists():
                    side_status = PlanStatus.REVIEW
                    side_reason = "Sidecar destination already exists."
                if dst_sidecar in claimed_destinations and claimed_destinations[dst_sidecar] != src_sidecar:
                    side_status = PlanStatus.REVIEW
                    side_reason = "Sidecar destination collision."
                claimed_destinations[dst_sidecar] = src_sidecar

                operations.append(
                    PlannedOperation(
                        source=src_sidecar,
                        destination=dst_sidecar,
                        kind=item.kind,
                        confidence=item.confidence,
                        status=side_status,
                        action=OperationAction.MOVE,
                        reason=side_reason,
                        is_primary=False,
                        group_id=group_id,
                    )
                )

    _append_leftover_operations(
        operations,
        output_root,
        leftover_policy,
        claimed_destinations,
    )
    return operations
