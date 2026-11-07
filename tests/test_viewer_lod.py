"""scripts/lod.py: additive detail levels for the viewer, a voxel pyramid per segment."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))  # lod imports splat_format
_spec = importlib.util.spec_from_file_location("lod", ROOT / "scripts" / "lod.py")
assert _spec and _spec.loader
lod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lod)

SH0_DTYPE = np.dtype([(f, "<f4") for f in (
    "x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
    "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3",
)])


def _scene(n_pool: int = 20000, n_parts: tuple[int, ...] = (3000, 600, 5), seed: int = 0):
    rng = np.random.default_rng(seed)
    sizes = (n_pool, *n_parts)
    part = np.repeat(np.arange(len(sizes)), sizes).astype(np.uint16)
    n = len(part)
    s = np.zeros(n, SH0_DTYPE)
    xyz = rng.uniform(-0.25, 0.25, (n, 3)).astype(np.float32)  # dense: many rows per coarse voxel
    s["x"], s["y"], s["z"] = xyz.T
    s["opacity"] = rng.normal(0, 2, n)
    s["scale_0"] = s["scale_1"] = s["scale_2"] = np.log(rng.uniform(0.005, 0.05, n))
    s["rot_0"] = 1.0
    rgb = rng.integers(0, 255, (n, 3)).astype(np.uint8)
    size_mm = rng.integers(1, 50, n).astype(np.uint8)
    return s, xyz, part, rgb, size_mm


def test_levels_are_a_partition_and_coarse_levels_hold_one_row_per_voxel() -> None:
    s, xyz, part, _, _ = _scene()
    levels = lod.assign_levels(xyz, part, lod.importance(s))
    assert levels.min() >= 0 and levels.max() <= len(lod.VOXELS)
    for k, v in enumerate(lod.VOXELS):
        rows = np.flatnonzero(levels == k)
        q = np.floor((xyz[rows] - xyz.min(0)) / v).astype(np.int64)
        keys = np.c_[part[rows], q]
        assert len(np.unique(keys, axis=0)) == len(rows), f"level {k} has two rows in one voxel"
    # coarse levels are smaller than fine ones, and the first level covers every segment
    counts = np.bincount(levels, minlength=len(lod.VOXELS) + 1)
    assert counts[0] < counts[1] < counts[2]
    assert set(np.unique(part[levels == 0])) == set(np.unique(part))


def test_the_most_important_row_of_a_voxel_wins() -> None:
    xyz = np.array([[0.01, 0.01, 0.01], [0.02, 0.02, 0.02], [0.5, 0.5, 0.5]], np.float32)
    seg = np.zeros(3, np.uint16)
    levels = lod.assign_levels(xyz, seg, np.array([0.1, 0.9, 0.5], np.float32), voxels=(0.12,))
    assert list(levels) == [1, 0, 0]


def test_export_levels_writes_files_whose_union_is_the_scene(tmp_path: Path) -> None:
    s, xyz, part, rgb, size_mm = _scene()
    entries = lod.export_levels(tmp_path, s, xyz, part, rgb, size_mm)
    assert [e["level"] for e in entries] == list(range(len(lod.VOXELS) + 1))
    assert sum(e["count"] for e in entries) == len(xyz)
    seen = []
    for e in entries:
        n = e["count"]
        raw = (tmp_path / e["bin"]).read_bytes()
        assert len(raw) == n * 18
        assert (tmp_path / e["splat"]).stat().st_size == n * 32
        pts = np.frombuffer(raw, "<f4", n * 3).reshape(n, 3)
        seg = np.frombuffer(raw, "<u2", n, offset=n * 12)
        assert len(e["ranges"]) == int(part.max()) + 1
        for k, (a, b) in enumerate(e["ranges"]):
            assert (seg[a:b] == k).all()  # every segment is one range per level
        seen.append(pts)
    allpts = np.concatenate(seen)
    assert len(np.unique(allpts, axis=0)) == len(np.unique(xyz, axis=0))


def test_rows_out_of_segment_order_are_refused(tmp_path: Path) -> None:
    s, xyz, part, rgb, size_mm = _scene()
    try:
        lod.export_levels(tmp_path, s, xyz, part[::-1].copy(), rgb, size_mm)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
