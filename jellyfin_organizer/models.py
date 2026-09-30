from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class MediaKind(str, Enum):
    MOVIE = "Movie"
    TV = "TV"
    UNKNOWN = "Unknown"


class PlanStatus(str, Enum):
    READY = "READY"
    REVIEW = "REVIEW"
    SKIP = "SKIP"
    ERROR = "ERROR"
    APPLIED = "APPLIED"


class OperationAction(str, Enum):
    MOVE = "Move"
    DELETE = "Delete"


class LeftoverPolicy(str, Enum):
    LEAVE = "leave"
    MOVE = "move"
    DELETE = "delete"


@dataclass(slots=True)
class ParsedMedia:
    source: Path
    kind: MediaKind
    title: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlannedOperation:
    source: Path
    destination: Path | None
    kind: MediaKind
    confidence: float
    status: PlanStatus
    action: OperationAction = OperationAction.MOVE
    reason: str = ""
    is_primary: bool = True
    group_id: str = ""
