"""M1 definition of done (AGENTS.md S8): clean.npz / scene_points.bin from pipeline/01_clean.py."""

import json
import struct
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
NPZ = DERIVED / "clean.npz"
BIN = DERIVED / "scene_points.bin"
ROOM_LIMIT = 20.0

pytestmark = pytest.mark.skipif(
    not (NPZ.exists() and BIN.exists()),
    reason="run `uv run python pipeline/01_clean.py` first (needs the gitignored .ply in data/raw)",
)


@pytest.fixture(scope="module")
def clean() -> dict[str, np.ndarray]:
    with np.load(NPZ) as z:
        return {k: z[k] for k in z.files}


def test_kept_count_in_range(clean: dict[str, np.ndarray]) -> None:
    """clean_mask keeps the opaque, finite, in-room splats: 70-80 % of the real rows on both scans so far
    (boiler room 77.4 %, Equipment Room 73.9 %)."""
    n = len(clean["xyz"])
    stats = json.loads((DERIVED / "clean_stats.json").read_text())
    share = n / stats["real_rows"]
    assert 0.5 <= share <= 0.95, f"kept {n:,} of {stats['real_rows']:,} real rows ({share:.1%})"


def test_bounds_within_room_limit(clean: dict[str, np.ndarray]) -> None:
    xyz = clean["xyz"]
    assert xyz.dtype == np.float32 and xyz.shape[1] == 3
    assert np.isfinite(xyz).all()
    assert (np.abs(xyz) < ROOM_LIMIT).all()
    assert (np.abs(xyz) > 1e-3).any(axis=1).all(), "points collapsed at the origin survived"


def test_y_is_up(clean: dict[str, np.ndarray]) -> None:
    p1, p99 = np.percentile(clean["xyz"], [1, 99], axis=0)
    span = p99 - p1
    assert span[1] < span[0], f"y span {span[1]:.2f} should be smaller than x span {span[0]:.2f}"
    assert span[1] < span[2], f"y span {span[1]:.2f} should be smaller than z span {span[2]:.2f}"


def test_arrays_consistent(clean: dict[str, np.ndarray]) -> None:
    n = len(clean["xyz"])
    assert clean["rgb"].shape == (n, 3) and clean["rgb"].dtype == np.uint8
    assert clean["opacity"].shape == (n,) and (clean["opacity"] >= 0.05).all()
    assert clean["scale"].shape == (n, 3) and (clean["scale"] < 2.0).all()
    assert clean["src_index"].shape == (n,) and len(np.unique(clean["src_index"])) == n


def test_scene_points_bin_layout() -> None:
    raw = BIN.read_bytes()
    (count,) = struct.unpack_from("<I", raw, 0)
    assert 0 < count <= 400_000, f"scene_points.bin holds {count:,} points, budget is 400 k"
    assert len(raw) == 4 + count * 12 + count * 3
    xyz = np.frombuffer(raw, dtype="<f4", count=count * 3, offset=4).reshape(-1, 3)
    assert np.isfinite(xyz).all() and (np.abs(xyz) < ROOM_LIMIT).all()
