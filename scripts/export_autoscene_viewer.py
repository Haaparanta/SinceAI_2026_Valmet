"""Export the automatic build (autoscene/out/scene.json + objects.npz) for the web viewer, in the same format as
scripts/export_viewer_scene.py writes for the manual build.

    uv run python scripts/export_autoscene_viewer.py          # -> data/derived/viewer_auto/scene.bin + scene.json

The viewer then shows it at http://localhost:5173/?scene=auto (capture.html takes the same parameter). Point order:
the pool (kept splats no object claimed) first, then every object in build order as one contiguous range, so
"the room after k objects" is a prefix of the objects block, exactly like the manual parts.

scene.bin, little-endian, n = total points:
    float32 xyz[n*3] | uint16 part[n] (0 = pool, k = parts[k-1]) | uint8 rgb[n*3] | uint8 size_mm[n]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[1]
AUTOSCENE = ROOT / "autoscene"
sys.path.insert(0, str(AUTOSCENE))

from autoscene.orientation import FRAME
from autoscene.scene import cache_for
from autoscene.splats import load_real_splats, rgb_of, size_of, xyz_of

OUT = ROOT / "data" / "derived" / "viewer_auto"
KIND = {"structure": "structure", "yoloe": "object", "cluster": "cluster"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", type=Path, default=AUTOSCENE / "out" / "scene.json")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--pool-max", type=int, default=0,
                    help="keep at most this many pool points (seeded random subset; 0 = all). Objects are never thinned.")
    args = ap.parse_args()

    scene = orjson.loads(args.scene.read_bytes())
    out_dir = args.scene.parent
    z = np.load(out_dir / "objects.npz")
    state = np.load(out_dir / "state.npz")
    ply = AUTOSCENE / "data" / "raw" / scene["source"]
    splats = load_real_splats(ply, cache_for(ply))
    objects = scene["objects"]
    offsets = np.r_[0, np.cumsum(z["sizes"])]
    assert len(objects) == len(z["sizes"]), "scene.json and objects.npz disagree: rerun the rebuild stage"

    claimed = np.zeros(len(splats), dtype=bool)
    claimed[z["splats"]] = True
    pool_idx = np.flatnonzero(state["keep"] & ~claimed).astype(np.int64)
    pool_total = len(pool_idx)
    if args.pool_max and pool_total > args.pool_max:
        pool_idx = np.sort(np.random.default_rng(0).choice(pool_idx, args.pool_max, replace=False))

    parts_meta, order, part_ids = [], [pool_idx], [np.zeros(len(pool_idx), np.uint16)]
    start = len(pool_idx)
    for k, obj in enumerate(objects, 1):
        idx = z["splats"][offsets[k - 1]:offsets[k]].astype(np.int64)
        order.append(idx)
        part_ids.append(np.full(len(idx), k, np.uint16))
        parts_meta.append({
            "seq": k, "step": obj["index"], "name": obj["name"], "label": obj["label"],
            "kind": KIND.get(obj["source"], "object"), "source": obj["source"], "confidence": obj["confidence"],
            "count": len(idx), "start": start, "end": start + len(idx), "bbox": obj["aabb"], "obb": obj["obb"],
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

    bounds = scene["room_bounds_p1_p99"]
    a, b, c = scene["floor_plane"]
    floor_y = a * 0.5 * (bounds["min"][0] + bounds["max"][0]) + b * 0.5 * (bounds["min"][2] + bounds["max"][2]) + c
    meta = {
        "version": 1, "build": "autoscene",
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {"file": scene["source"], "header_rows": len(splats), "real_rows": len(splats)},
        "frame": FRAME, "units": scene["units"], "up_axis": "y",
        "count": len(rows), "pool_count": len(pool_idx), "pool_total": int(pool_total),
        "removed_count": int(len(splats) - int(state["keep"].sum())),
        "room_bounds": bounds, "floor_y": round(float(floor_y), 4),
        "dollhouse_cut_y": round(float(scene["ceiling_y"]) - 0.75, 3),
        "layout": "float32 xyz[n*3] | uint16 part[n] | uint8 rgb[n*3] | uint8 size_mm[n]",
        "by_label": scene["by_label"], "by_source": scene["by_source"],
        "parts": parts_meta,
    }
    (args.out / "scene.json").write_bytes(orjson.dumps(meta, option=orjson.OPT_INDENT_2) + b"\n")
    mb = (args.out / "scene.bin").stat().st_size / 1e6
    print(f"{len(rows):,} points ({len(pool_idx):,} pool of {pool_total:,}, {len(parts_meta)} objects) "
          f"-> {args.out.relative_to(ROOT)}/scene.bin ({mb:.1f} MB) + scene.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
