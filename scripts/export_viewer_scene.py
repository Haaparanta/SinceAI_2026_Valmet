"""Export the step-by-step build (build/manifest.json + part indices) for the web viewer and the snapshot page.

    uv run python scripts/export_viewer_scene.py            # -> data/derived/viewer/scene.bin + scene.json

Reads only: the manifest, build/parts/*.idx.npy, build/removed/*.idx.npy and the SH-0 world-frame cache of the master
scan (pipeline/build.py writes it on its first run). Writes nothing outside data/derived/viewer/.

Point order: the pool (kept, not yet claimed by a part) first, then every accepted part in acceptance order, so each
part is one contiguous range [start, end) and "the twin after k parts" is a prefix of the parts block.

scene.bin, little-endian, n = total points:
    float32 xyz[n*3] | uint16 part[n] (0 = pool, k = parts[k-1]) | uint8 rgb[n*3] | uint8 size_mm[n]
size_mm = splat render footprint (stepbuild.splats.size_of) in 1/1000 scene units, clamped to 1..255.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from common.orientation import FRAME
from stepbuild import state as S
from stepbuild.splats import rgb_of, size_of, xyz_of

OUT = ROOT / "data" / "derived" / "viewer"


def cache_for(ply_name: str, ply_size: int) -> Path:
    """Same naming as pipeline/build.py::cache_for (frame, stem, byte size)."""
    stem = "".join(c if c.isalnum() else "_" for c in Path(ply_name).stem).strip("_")
    return ROOT / "data" / "derived" / f"real_sh0_{FRAME}_{stem}_{ply_size}.npy"


def find_cache(source_file: str) -> Path:
    raw = ROOT / "data" / "raw" / source_file
    if raw.exists():
        path = cache_for(source_file, raw.stat().st_size)
        if path.exists():
            return path
    stem = "".join(c if c.isalnum() else "_" for c in Path(source_file).stem).strip("_")
    hits = sorted((ROOT / "data" / "derived").glob(f"real_sh0_{FRAME}_{stem}_*.npy"))
    if not hits:
        raise SystemExit(f"no SH-0 cache for {source_file!r} in data/derived: run `uv run python pipeline/build.py` "
                         "once (it writes the cache), or copy it from the worktree that has it")
    return hits[-1]


def bbox(xyz: np.ndarray) -> dict:
    return {"min": [round(float(v), 4) for v in xyz.min(0)], "max": [round(float(v), 4) for v in xyz.max(0)]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=S.MANIFEST)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--pool-max", type=int, default=0,
                    help="keep at most this many pool points (seeded random subset; 0 = all). Parts are never thinned.")
    args = ap.parse_args()

    m = S.Manifest.load(args.manifest)
    real_rows = m.data["source"]["real_rows"]
    cache = find_cache(m.data["source"]["file"])
    splats = np.load(cache, mmap_mode="r")
    if len(splats) != real_rows:
        raise SystemExit(f"{cache.name} has {len(splats):,} rows, the manifest expects {real_rows:,}")

    pool = m.pool_mask()
    pool_idx = np.flatnonzero(pool).astype(np.int64)
    pool_total = len(pool_idx)
    if args.pool_max and pool_total > args.pool_max:
        pool_idx = np.sort(np.random.default_rng(0).choice(pool_idx, args.pool_max, replace=False))

    parts_meta, order, part_ids = [], [pool_idx], [np.zeros(len(pool_idx), np.uint16)]
    start = len(pool_idx)
    for k, p in enumerate(m.data["parts"], 1):
        idx = np.load(ROOT / p["indices"]).astype(np.int64)
        order.append(idx)
        part_ids.append(np.full(len(idx), k, np.uint16))
        parts_meta.append({
            "seq": k, "step": p["index"], "name": p["name"], "label": p.get("label", p["name"]),
            "kind": p.get("kind", "object"), "count": len(idx), "start": start, "end": start + len(idx),
            "bbox": p.get("bbox") or bbox(xyz_of(splats[idx])),
        })
        start += len(idx)

    rows = np.concatenate(order)
    sel = splats[rows]
    xyz = xyz_of(sel)
    rgb = rgb_of(sel)
    size_mm = np.clip(np.rint(size_of(sel) * 1000.0), 1, 255).astype(np.uint8)
    part = np.concatenate(part_ids)

    args.out.mkdir(parents=True, exist_ok=True)
    tmp = args.out / "scene.bin.tmp"
    with tmp.open("wb") as f:
        for arr in (xyz.astype("<f4"), part.astype("<u2"), rgb, size_mm):
            f.write(np.ascontiguousarray(arr).tobytes())
    tmp.replace(args.out / "scene.bin")

    bounds = m.data.get("room_bounds_p1_p99") or bbox(xyz)
    floor = next((p for p in parts_meta if p["name"] == "floor"), None)
    floor_y = float(np.median(xyz[floor["start"]:floor["end"], 1])) if floor else float(bounds["min"][1])
    meta = {
        "version": 1,
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": m.data["source"], "frame": m.data.get("frame", FRAME), "units": m.data.get("units", "scene_units"),
        "up_axis": m.data.get("up_axis", "y"),
        "count": len(rows), "pool_count": len(pool_idx), "pool_total": int(pool_total),
        "removed_count": int(real_rows - pool_total - sum(p["count"] for p in parts_meta)),
        "room_bounds": bounds, "floor_y": round(floor_y, 4),
        "dollhouse_cut_y": m.data.get("dollhouse_cut_y"),
        "layout": "float32 xyz[n*3] | uint16 part[n] | uint8 rgb[n*3] | uint8 size_mm[n]",
        "parts": parts_meta,
    }
    (args.out / "scene.json").write_bytes(orjson.dumps(meta, option=orjson.OPT_INDENT_2) + b"\n")
    mb = (args.out / "scene.bin").stat().st_size / 1e6
    print(f"{len(rows):,} points ({len(pool_idx):,} pool of {pool_total:,}, {len(parts_meta)} parts) "
          f"-> {args.out.relative_to(ROOT)}/scene.bin ({mb:.1f} MB) + scene.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
