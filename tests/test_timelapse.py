"""scripts/timelapse.py: the timing plan keeps every video between --min and --max seconds."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("timelapse", Path(__file__).parents[1] / "scripts" / "timelapse.py")
assert _spec and _spec.loader
timelapse = importlib.util.module_from_spec(_spec)
sys.modules["timelapse"] = timelapse  # @dataclass looks its module up here
_spec.loader.exec_module(timelapse)


def _paths(n: int) -> list[Path]:
    return [Path(f"{i:04d}_20261107-000000.png") for i in range(1, n + 1)]


@pytest.mark.parametrize("n", [1, 5, 100, 180, 354, 641, 5000])
def test_duration_is_clamped(n: int) -> None:
    p = timelapse.plan(_paths(n), min_s=30, max_s=60, rate=6, fps=30, hold_last=2)
    assert 30 <= p.seconds <= 60
    assert all(f >= 1 for f in p.frames)
    assert p.images[0].name.startswith("0001") and p.images[-1] == _paths(n)[-1]


@pytest.mark.parametrize("max_s", [59.99, 45.5, 31.01])
def test_fractional_max_never_rounds_up(max_s: float) -> None:
    p = timelapse.plan(_paths(5000), min_s=30, max_s=max_s, rate=6, fps=30, hold_last=2)
    assert p.seconds <= max_s


def test_many_images_are_thinned_in_order() -> None:
    p = timelapse.plan(_paths(5000), min_s=30, max_s=60, rate=6, fps=30, hold_last=0)
    assert len(p.images) == 1800
    assert p.images == sorted(p.images)


def test_collect_filters_by_index(tmp_path: Path) -> None:
    for name in ["0001_a.png", "0002_b.png", "0010_c.jpg", "notes.txt", "x.png"]:
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in timelapse.collect(tmp_path, first=2, last=10)] == ["0002_b.png", "0010_c.jpg"]


def test_bad_bounds() -> None:
    with pytest.raises(ValueError):
        timelapse.plan(_paths(3), min_s=60, max_s=30, rate=6, fps=30)
    with pytest.raises(ValueError):
        timelapse.plan([], min_s=30, max_s=60, rate=6, fps=30)
    with pytest.raises(ValueError):
        timelapse.plan(_paths(3), min_s=30, max_s=60, rate=0, fps=30)


@pytest.mark.parametrize("n", [1, 5, 354, 757, 5000])
def test_cards_count_toward_the_limit(n: int) -> None:
    p = timelapse.plan(_paths(n), min_s=30, max_s=60, rate=6, fps=30, hold_last=2, intro_s=3, outro_s=4)
    assert 30 <= p.seconds <= 60
    assert (p.intro, p.outro) == (90, 120)
    assert all(f >= 1 for f in p.frames)


def test_cards_longer_than_min_are_rejected() -> None:
    with pytest.raises(ValueError):
        timelapse.plan(_paths(10), min_s=30, max_s=60, rate=6, fps=30, hold_last=2, intro_s=15, outro_s=15)


@pytest.mark.parametrize("plain", [False, True])
def test_frame_stream_matches_plan(tmp_path: Path, plain: bool) -> None:
    from PIL import Image

    paths = []
    for i in range(1, 8):
        path = tmp_path / f"{i:04d}_20261107-0{i}0000.png"
        Image.new("RGB", (64, 40) if i != 3 else (50, 50), (i * 30, 0, 0)).save(path)  # one odd size: letterboxed
        paths.append(path)
    intro, outro = (0, 0) if plain else (1, 1)
    p = timelapse.plan(paths, min_s=4, max_s=6, rate=6, fps=10, hold_last=0.5, intro_s=intro, outro_s=outro)
    style = None if plain else timelapse.Style(found=len(paths))
    frames = list(timelapse.frame_stream(p, (64, 40), style))
    assert len(frames) == p.total_frames
    assert {f.size for f in frames} == {(64, 40)}


def test_count_objects_reads_autoscene_names() -> None:
    names = [
        "0001_20261107-031921_001_floor_1_a.png",
        "0002_20261107-031921_001_floor_1_b.png",
        "0021_20261107-031941_007_chair_1_c.png",
        "1271_20261107-032950_424_unidentified_object_76_b.png",
        "1275_20261107-033012_all_objects_coloured.png",
    ]
    assert timelapse.count_objects([Path(n) for n in names]) == 3
