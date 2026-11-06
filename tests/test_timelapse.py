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
