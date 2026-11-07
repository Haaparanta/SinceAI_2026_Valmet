"""Detail levels (LOD) for the viewer, generated offline next to scene.bin / scene.splat.

The rows are split into additive levels: level 0 is a coarse but complete room, every next level adds detail, and all
levels together are exactly the full scene (no row twice). The viewer streams them in order, coarse first, and in VR
it can leave out the finest levels to hold the frame rate.

Selection is a voxel pyramid per segment (segment 0 = the pool, k = part k): for each voxel size in VOXELS, coarse to
fine, the most important remaining row in every occupied voxel goes to that level; whatever is left after the finest
voxel size is the last level. Importance = opacity x footprint (the opaque, large splats carry a coarse view).
Working per segment keeps every part present at every level, so replay and selection work while detail streams in.

Files, for L = len(VOXELS) + 1 levels, in <out>/lod/:
    <k>.bin    the scene.bin layout: float32 xyz | uint16 part | uint8 rgb | uint8 size_mm
    <k>.splat  the .splat layout of splat_format.py
Inside a level the rows keep the segment order of scene.bin (pool, then parts in build order), so each segment is one
[start, end) range per level; scene.json lists them under "lods".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from splat_format import write_splat

#: voxel edge per level, scene units, coarse to fine; one more level holds the rest
VOXELS: tuple[float, ...] = (0.12, 0.06, 0.03, 0.015)


def importance(s: np.ndarray) -> np.ndarray:
    """Opacity x longest linear scale (clamped), from the INRIA SH-0 fields."""
    alpha = 1.0 / (1.0 + np.exp(-np.clip(np.nan_to_num(s["opacity"], nan=-30.0), -30.0, 30.0)))
    log_scale = np.maximum(np.maximum(s["scale_0"], s["scale_1"]), s["scale_2"])
    longest = np.exp(np.clip(np.nan_to_num(log_scale, nan=-30.0), -30.0, np.log(0.1)))
    return (alpha * longest).astype(np.float32)


def assign_levels(xyz: np.ndarray, segment: np.ndarray, imp: np.ndarray,
                  voxels: tuple[float, ...] = VOXELS) -> np.ndarray:
    """uint8 level per row: 0..len(voxels)-1 from the voxel pyramid, len(voxels) for the rest."""
    n = len(xyz)
    level = np.full(n, len(voxels), np.uint8)
    if n == 0:
        return level
    xyz = np.nan_to_num(np.asarray(xyz, np.float64))
    lo = xyz.min(0)
    remaining = np.arange(n)
    for k, v in enumerate(voxels):
        if len(remaining) == 0:
            break
        q = np.floor((xyz[remaining] - lo) / v).astype(np.int64)
        seg = segment[remaining].astype(np.int64)
        # group by (segment, voxel), most important first inside a group (lexsort: last key is the primary one)
        order = np.lexsort((-imp[remaining], q[:, 2], q[:, 1], q[:, 0], seg))
        keys = np.stack([seg[order], q[order, 0], q[order, 1], q[order, 2]], 1)
        first = np.r_[True, np.any(keys[1:] != keys[:-1], axis=1)]
        chosen = order[first]
        level[remaining[chosen]] = k
        keep = np.ones(len(remaining), bool)
        keep[chosen] = False
        remaining = remaining[keep]
    return level


def write_points_bin(path: Path, xyz: np.ndarray, part: np.ndarray, rgb: np.ndarray, size_mm: np.ndarray) -> None:
    """The scene.bin layout, written atomically."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        for arr in (np.asarray(xyz, "<f4"), np.asarray(part, "<u2"), np.asarray(rgb, np.uint8),
                    np.asarray(size_mm, np.uint8)):
            f.write(np.ascontiguousarray(arr).tobytes())
    tmp.replace(path)


def export_levels(out: Path, splats: np.ndarray, xyz: np.ndarray, part: np.ndarray, rgb: np.ndarray,
                  size_mm: np.ndarray, voxels: tuple[float, ...] = VOXELS) -> list[dict]:
    """Write <out>/lod/<k>.{bin,splat} for rows already in scene.bin order; return the scene.json "lods" entries.

    `part` is the segment of every row (0 = pool, k = part k) and must be non-decreasing, which the exporters' row order
    (pool first, then parts in build order) guarantees.
    """
    part = np.asarray(part)
    if len(part) and np.any(np.diff(part.astype(np.int64)) < 0):
        raise ValueError("rows must be grouped by segment (pool first, then parts in order)")
    n_segments = int(part.max()) + 1 if len(part) else 1
    levels = assign_levels(xyz, part, importance(splats), voxels)
    lod_dir = out / "lod"
    lod_dir.mkdir(parents=True, exist_ok=True)
    for stale in lod_dir.glob("*"):
        if stale.suffix in (".bin", ".splat", ".tmp"):
            stale.unlink()
    entries = []
    for k in range(len(voxels) + 1):
        idx = np.flatnonzero(levels == k)  # ascending, so the segment order of the rows is kept
        seg = part[idx]
        starts = np.searchsorted(seg, np.arange(n_segments), "left")
        ends = np.searchsorted(seg, np.arange(n_segments), "right")
        write_points_bin(lod_dir / f"{k}.bin", xyz[idx], seg, rgb[idx], size_mm[idx])
        write_splat(lod_dir / f"{k}.splat", splats[idx])
        entries.append({
            "level": k, "voxel": voxels[k] if k < len(voxels) else None, "count": len(idx),
            "bin": f"lod/{k}.bin", "splat": f"lod/{k}.splat",
            "ranges": [[int(a), int(b)] for a, b in zip(starts, ends, strict=True)],
        })
    return entries
