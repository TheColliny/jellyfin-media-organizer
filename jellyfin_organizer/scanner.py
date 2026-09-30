from __future__ import annotations

from pathlib import Path

from .parser import is_extra_video, is_video, parse_media
from .models import ParsedMedia


def scan_roots(roots: list[Path]) -> list[ParsedMedia]:
    seen: set[Path] = set()
    items: list[ParsedMedia] = []

    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if not is_video(path):
                continue
            if is_extra_video(path):
                continue

            try:
                resolved = path.resolve()
            except OSError:
                resolved = path

            if resolved in seen:
                continue
            seen.add(resolved)
            items.append(parse_media(path))

    return items
