"""M1 - Clean scan loader (AGENTS.md S3, 02 S3 M1).

Reads the 3DGS PLY with numpy, keeps only the real-row prefix (the header count is wrong), applies `clean_mask`, and writes to data/derived/:
  clean.npz         xyz float32[n,3] | rgb uint8[n,3] | opacity float32[n] | scale float32[n,3] (linear) | src_index uint32[n]
  scene_points.bin  uint32 count | float32 xyz*count | uint8 rgb*count   (voxel-downsampled to <= --max-points)
  clean_stats.json  kept count, bounds per axis, floor_y, voxel size      (the browser reads its numbers from here)

Idempotent. Logs kept count, bounds per axis, up axis and the detected floor y (densest thin slab on y).

    uv run python pipeline/01_clean.py [--in PLY] [--out DIR] [--max-points 400000]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import orjson
from common.orientation import FRAME, to_world
from common.ply_io import clean_mask, load_gaussians, rgb_from_dc
from common.splat_rows import real_row_count

log = logging.getLogger("01_clean")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "raw" / "Industrial Boiler Room (1).ply"
DEFAULT_OUT = ROOT / "data" / "derived"


def detect_floor_y(y: np.ndarray, slab: float = 0.02) -> tuple[float, int]:
    """Floor = densest `slab`-thick y slab in the lower half of the p1..p99 y-range. Returns (floor_y, points in slab)."""
    lo, hi = np.percentile(y, [1, 99])
    edges = np.arange(lo, 0.5 * (lo + hi) + slab, slab)
    counts, edges = np.histogram(y, bins=edges)
    k = int(np.argmax(counts))
    return float(0.5 * (edges[k] + edges[k + 1])), int(counts[k])


def voxel_downsample(
    xyz: np.ndarray, rgb: np.ndarray, max_points: int, voxel: float = 0.005
) -> tuple[np.ndarray, np.ndarray, float]:
    """Average xyz/rgb per voxel; grow the voxel by 25 % until the result has <= max_points. Returns (xyz, rgb, voxel)."""
    origin = xyz.min(0)
    while True:
        keys = np.floor((xyz - origin) / voxel).astype(np.int64)
        dims = keys.max(0) + 1
        flat = (keys[:, 0] * dims[1] + keys[:, 1]) * dims[2] + keys[:, 2]
        uniq, inv = np.unique(flat, return_inverse=True)
        if len(uniq) <= max_points:
            break
        voxel *= 1.25
    n = len(uniq)
    cnt = np.bincount(inv, minlength=n).astype(np.float64)[:, None]
    out_xyz = np.stack([np.bincount(inv, weights=xyz[:, i], minlength=n) for i in range(3)], 1) / cnt
    out_rgb = np.stack([np.bincount(inv, weights=rgb[:, i], minlength=n) for i in range(3)], 1) / cnt
    return out_xyz.astype(np.float32), np.clip(np.rint(out_rgb), 0, 255).astype(np.uint8), float(voxel)


def write_scene_points(path: Path, xyz: np.ndarray, rgb: np.ndarray) -> None:
    """scene_points.bin: uint32 count, count x float32[3] xyz, count x uint8[3] rgb (little-endian)."""
    with open(path, "wb") as f:
        f.write(np.uint32(len(xyz)).tobytes())
        f.write(np.ascontiguousarray(xyz, dtype="<f4").tobytes())
        f.write(np.ascontiguousarray(rgb, dtype=np.uint8).tobytes())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN, help="3DGS PLY (default: data/raw/...)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default: data/derived)")
    ap.add_argument("--max-points", type=int, default=400_000, help="point budget for scene_points.bin")
    ap.add_argument("--room-limit", type=float, default=20.0, help="|x,y,z| must be below this (scene units)")
    ap.add_argument("--min-opacity", type=float, default=0.05)
    ap.add_argument("--max-scale", type=float, default=2.0, help="max linear gaussian scale (scene units)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if not args.inp.exists():
        log.error("PLY not found: %s  (ln -s ../Source-Data-Do-Not_change data/raw ; the .ply is gitignored)", args.inp)
        return 2

    t0 = time.perf_counter()
    g = load_gaussians(str(args.inp))
    log.info("loaded %s gaussians x %d float32 fields in %.1f s", f"{len(g):,}", len(g.dtype.names), time.perf_counter() - t0)
    header_rows = len(g)
    # The header count of this file is wrong: only a contiguous prefix holds trained splats, the tail is random bits
    # (analysis/ply_study/README.md S2). Keep the prefix before any filtering.
    real_rows, plausible_after = real_row_count(g)
    g = to_world(g[:real_rows])  # stored upside down and mirrored: rotate 180 deg about z (common/orientation.py)
    log.info(
        "real rows: %s of %s (header count); dropped garbage tail of %s rows (%d of them look plausible)",
        f"{real_rows:,}", f"{header_rows:,}", f"{header_rows - real_rows:,}", plausible_after,
    )

    with np.errstate(invalid="ignore"):  # NaN opacity/scale rows are rejected by the comparisons, no need to warn
        mask = clean_mask(g, room_limit=args.room_limit, min_opacity=args.min_opacity, max_scale=args.max_scale)
    # clean_mask (AGENTS.md S3) does not check the colour fields: drop the few gaussians whose f_dc is NaN
    colour_ok = np.isfinite(np.stack([g["f_dc_0"], g["f_dc_1"], g["f_dc_2"]], 1)).all(1)
    nan_colour = int((mask & ~colour_ok).sum())
    mask &= colour_ok
    kept = int(mask.sum())
    log.info(
        "kept %s / %s real gaussians (%.1f %%); dropped %d with NaN colour",
        f"{kept:,}", f"{len(g):,}", 100.0 * kept / len(g), nan_colour,
    )
    gk = g[mask]
    xyz = np.stack([gk["x"], gk["y"], gk["z"]], 1).astype(np.float32)
    rgb = np.rint(rgb_from_dc(gk) * 255.0).astype(np.uint8)
    opacity = (1.0 / (1.0 + np.exp(-np.clip(gk["opacity"], -30, 30)))).astype(np.float32)
    scale = np.exp(np.clip(np.stack([gk["scale_0"], gk["scale_1"], gk["scale_2"]], 1), -30, 30)).astype(np.float32)
    src_index = np.flatnonzero(mask).astype(np.uint32)
    del g, gk

    bmin, bmax = xyz.min(0), xyz.max(0)
    p1, p99 = np.percentile(xyz, [1, 99], axis=0)
    span = p99 - p1
    up_axis = "xyz"[int(np.argmin(span))]  # the vertical axis has the smallest p1..p99 extent in a room [HYPOTHESIS]
    floor_y, floor_n = detect_floor_y(xyz[:, 1])
    for i, a in enumerate("xyz"):
        log.info(
            "bounds %s: min %+.3f  p1 %+.3f  p99 %+.3f  max %+.3f   (p1..p99 span %.2f u)",
            a, bmin[i], p1[i], p99[i], bmax[i], span[i],
        )
    log.info("up axis by smallest span: %s (expected y)", up_axis)
    log.info("floor_y = %+.3f u  (densest 0.02 u slab on y, %s points)", floor_y, f"{floor_n:,}")

    args.out.mkdir(parents=True, exist_ok=True)
    np.savez(args.out / "clean.npz", xyz=xyz, rgb=rgb, opacity=opacity, scale=scale, src_index=src_index)
    dxyz, drgb, voxel = voxel_downsample(xyz, rgb.astype(np.float32), args.max_points)
    write_scene_points(args.out / "scene_points.bin", dxyz, drgb)
    stats = {
        "source_file": args.inp.name,
        "total": header_rows,
        "real_rows": real_rows,
        "garbage_rows": header_rows - real_rows,
        "plausible_after_real": plausible_after,
        "kept": kept,
        "scene_points": len(dxyz),
        "voxel_size": round(voxel, 5),
        "units": "scene_units",
        "frame": FRAME,
        "up_axis": "y",
        "up_axis_detected": up_axis,
        "bounds_min": [round(float(v), 4) for v in bmin],
        "bounds_max": [round(float(v), 4) for v in bmax],
        "bounds_p1": [round(float(v), 4) for v in p1],
        "bounds_p99": [round(float(v), 4) for v in p99],
        "floor_y": round(floor_y, 4),
        "floor_slab_points": floor_n,
        "dropped_nan_colour": nan_colour,
        "thresholds": {
            "room_limit": args.room_limit, "min_opacity": args.min_opacity, "max_scale": args.max_scale,
        },
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (args.out / "clean_stats.json").write_bytes(orjson.dumps(stats, option=orjson.OPT_INDENT_2))
    log.info(
        "wrote %s (%s pts), %s (%s pts, voxel %.3f u), clean_stats.json in %.1f s",
        "clean.npz", f"{kept:,}", "scene_points.bin", f"{len(dxyz):,}", voxel, stats["elapsed_s"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
