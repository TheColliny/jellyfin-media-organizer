from pathlib import Path

from jellyfin_organizer.models import MediaKind
from jellyfin_organizer.parser import parse_media
from jellyfin_organizer.planner import build_plan


def test_tv_sxe():
    item = parse_media(Path("/media/Show.Name.2022/Season 1/Show.Name.S01E02.1080p.mkv"))
    assert item.kind == MediaKind.TV
    assert item.season == 1
    assert item.episode == 2
    assert item.title == "Show Name"


def test_tv_multi_episode():
    item = parse_media(Path("/media/Show/Show.S02E03-E04.mkv"))
    assert item.kind == MediaKind.TV
    assert item.season == 2
    assert item.episode == 3
    assert item.episode_end == 4


def test_movie():
    item = parse_media(Path("/media/Arrival.2016.1080p.BluRay.x264.mkv"))
    assert item.kind == MediaKind.MOVIE
    assert item.title == "Arrival"
    assert item.year == 2016


def test_movie_plan():
    item = parse_media(Path("/source/Arrival.2016.1080p.BluRay.x264.mkv"))
    plan = build_plan([item], Path("/organized"))
    assert plan[0].destination == Path("/organized/Movies/Arrival (2016)/Arrival (2016).mkv")


def test_leftover_move_policy(tmp_path):
    from jellyfin_organizer.models import LeftoverPolicy, OperationAction, PlanStatus

    source_dir = tmp_path / "Incoming" / "Example.Movie.2020"
    source_dir.mkdir(parents=True)
    video = source_dir / "Example.Movie.2020.mkv"
    poster = source_dir / "poster.jpg"
    video.write_bytes(b"video")
    poster.write_bytes(b"poster")
    output = tmp_path / "Library"
    output.mkdir()

    item = parse_media(video)
    plan = build_plan([item], output, leftover_policy=LeftoverPolicy.MOVE)
    leftover = next(op for op in plan if op.source == poster)
    assert leftover.status == PlanStatus.READY
    assert leftover.action == OperationAction.MOVE
    assert leftover.destination == output / "Movies" / "Example Movie (2020)" / "poster.jpg"


def test_ambiguous_flat_folder_leftover_is_review(tmp_path):
    from jellyfin_organizer.models import LeftoverPolicy, PlanStatus

    source_dir = tmp_path / "Incoming"
    source_dir.mkdir()
    first = source_dir / "First.Movie.2020.mkv"
    second = source_dir / "Second.Movie.2021.mkv"
    note = source_dir / "readme.txt"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    note.write_text("unrelated or ambiguous", encoding="utf-8")
    output = tmp_path / "Library"
    output.mkdir()

    plan = build_plan(
        [parse_media(first), parse_media(second)],
        output,
        leftover_policy=LeftoverPolicy.DELETE,
    )
    leftover = next(op for op in plan if op.source == note)
    assert leftover.status == PlanStatus.REVIEW
    assert leftover.destination is None
