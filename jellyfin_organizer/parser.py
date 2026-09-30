from __future__ import annotations

import re
from pathlib import Path

from .models import MediaKind, ParsedMedia

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".m4v", ".avi", ".mov", ".webm", ".wmv",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".mts"
}

SIDECAR_EXTENSIONS = {
    ".srt", ".ass", ".ssa", ".vtt", ".sub", ".idx", ".nfo",
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".aac", ".ac3", ".eac3", ".dts", ".flac", ".mp3", ".m4a", ".mka"
}

EXTRA_FOLDER_NAMES = {
    "behind the scenes", "deleted scenes", "interviews", "scenes",
    "samples", "shorts", "featurettes", "clips", "other", "extras",
    "trailers", "theme-music", "backdrops"
}

EXTRA_STEM_RE = re.compile(
    r"(?:^|[-._ ])(?:trailer|sample|scene|clip|interview|behindthescenes|"
    r"deleted|deletedscene|featurette|short|other|extra)$",
    re.IGNORECASE,
)

TV_PATTERNS = [
    re.compile(
        r"(?i)(?P<season>\d{1,2})x(?P<episode>\d{1,3})"
    ),
    re.compile(
        r"(?i)\bS(?P<season>\d{1,3})E(?P<episode>\d{1,3})"
        r"(?:[-_. ]?E?(?P<episode_end>\d{1,3}))?\b"
    ),
]

YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)")

# Common release-name tokens that usually are not part of a title.
NOISE_RE = re.compile(
    r"(?ix)"
    r"\b(?:"
    r"2160p|1080p|1080i|720p|576p|480p|4k|uhd|hdr10\+?|hdr|dv|dolby[ ._-]?vision|"
    r"bluray|blu[ ._-]?ray|bdrip|brrip|webrip|web[ ._-]?dl|hdtv|dvdrip|remux|"
    r"x26[45]|h\.?26[45]|hevc|av1|xvid|divx|"
    r"aac(?:2\.0|5\.1|7\.1)?|ac3|eac3|ddp(?:2\.0|5\.1|7\.1)?|dts(?:-hd)?|truehd|atmos|"
    r"proper|repack|internal|limited|extended|unrated|remastered|"
    r"multi|dual[ ._-]?audio"
    r")\b"
)

BRACKET_RELEASE_RE = re.compile(r"[\[\{][^\]\}]{1,40}[\]\}]")
MULTISPACE_RE = re.compile(r"\s+")


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_extra_video(path: Path) -> bool:
    if any(parent.name.lower() in EXTRA_FOLDER_NAMES for parent in path.parents):
        return True
    return bool(EXTRA_STEM_RE.search(path.stem))


def _normalize_text(text: str) -> str:
    text = text.replace("_", " ").replace(".", " ")
    text = BRACKET_RELEASE_RE.sub(" ", text)
    text = NOISE_RE.sub(" ", text)
    text = re.sub(r"\s+-\s+[A-Za-z0-9]{2,20}$", " ", text)  # likely release group
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip(" -._")


def _title_case_conservative(text: str) -> str:
    # Preserve intentional capitalization if source already has mixed case.
    if any(c.islower() for c in text) and any(c.isupper() for c in text):
        return MULTISPACE_RE.sub(" ", text).strip()
    return MULTISPACE_RE.sub(" ", text).strip().title()


def _extract_year(text: str) -> tuple[int | None, str]:
    matches = list(YEAR_RE.finditer(text))
    if not matches:
        return None, text
    # Prefer the last plausible year because release names often put it after title.
    match = matches[-1]
    year = int(match.group(1))
    cleaned = (text[:match.start()] + " " + text[match.end():]).strip()
    return year, cleaned


def _parent_title_hint(path: Path) -> tuple[str | None, int | None]:
    parent = path.parent
    if re.match(r"(?i)^season[ ._-]*\d+$", parent.name):
        parent = parent.parent
    if not parent.name:
        return None, None
    cleaned = _normalize_text(parent.name)
    year, cleaned = _extract_year(cleaned)
    cleaned = _title_case_conservative(cleaned)
    return (cleaned or None), year


def parse_media(path: Path) -> ParsedMedia:
    stem = path.stem

    for pattern in TV_PATTERNS:
        match = pattern.search(stem)
        if match:
            season = int(match.group("season"))
            episode = int(match.group("episode"))
            episode_end_raw = match.groupdict().get("episode_end")
            episode_end = int(episode_end_raw) if episode_end_raw else None

            before = stem[:match.start()]
            cleaned_before = _normalize_text(before)
            file_year, cleaned_before = _extract_year(cleaned_before)
            title = _title_case_conservative(cleaned_before)

            parent_title, parent_year = _parent_title_hint(path)
            confidence = 0.92
            notes = []

            if parent_title and (not title or len(title) < 2):
                title = parent_title
                confidence = 0.95
                notes.append("Series title taken from parent folder.")
            elif parent_title and title:
                # Prefer parent hierarchy when the filename prefix appears generic/noisy.
                if title.lower() in {"episode", "show", "tv"}:
                    title = parent_title
                    confidence = 0.94
                    notes.append("Series title taken from parent folder.")

            if not title:
                title = parent_title or "Unknown Series"
                confidence = 0.55
                notes.append("Could not reliably determine series title.")

            year = file_year or parent_year
            return ParsedMedia(
                source=path,
                kind=MediaKind.TV,
                title=title,
                year=year,
                season=season,
                episode=episode,
                episode_end=episode_end,
                confidence=confidence,
                notes=notes,
            )

    cleaned = _normalize_text(stem)
    year, cleaned = _extract_year(cleaned)
    title = _title_case_conservative(cleaned)
    confidence = 0.82 if year and title else 0.68 if title else 0.25
    notes = []

    parent_title, parent_year = _parent_title_hint(path)

    # A file like "Movie.mkv" inside "Movie (2020)" benefits from the parent folder.
    if parent_title and year is None and parent_year is not None:
        if title.lower() == parent_title.lower() or len(title) < 3:
            title = parent_title
            year = parent_year
            confidence = 0.93
            notes.append("Movie title/year taken from parent folder.")

    if not title:
        title = "Unknown Movie"
        notes.append("Could not reliably determine movie title.")

    return ParsedMedia(
        source=path,
        kind=MediaKind.MOVIE,
        title=title,
        year=year,
        confidence=confidence,
        notes=notes,
    )
