"""Synthetic stand-in for data/derived/viewer/scene.{bin,json}, so the web viewer can be tested without the scan.

    uv run python scripts/make_viewer_fixture.py                # -> data/derived/viewer/ (refuses to replace a real export)
    uv run python scripts/make_viewer_fixture.py --out /tmp/v   # anywhere else

The real export (scripts/export_viewer_scene.py) needs the gitignored master .ply. This writes the same layout from the
committed build/manifest.json alone: every accepted part becomes a box of random points inside its manifest bbox, the
pool is a sparse haze over the room bounds. Part names, labels, kinds, order and bboxes match the real build, so URLs
like `?part=pipe_3` behave the same; colours and shapes do not. scene.json carries "fixture": true.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "build" / "manifest.json"
OUT = ROOT / "data" / "derived" / "viewer"

KIND_RGB = {"structure": (120, 124, 132), "object": (60, 150, 220)}


def build(manifest: dict, pool_points: int, part_points: int, seed: int = 0) -> tuple[bytes, dict]:
    rng = np.random.default_rng(seed)
    bounds = manifest["room_bounds_p1_p99"]
    lo, hi = np.array(bounds["min"], "f4"), np.array(bounds["max"], "f4")

    chunks = [(rng.uniform(lo, hi, (pool_points, 3)).astype("<f4"), 0, (70, 70, 80))]
    parts_meta, start = [], pool_points
    for k, p in enumerate(manifest["parts"], 1):
        b_lo, b_hi = np.array(p["bbox"]["min"], "f4"), np.array(p["bbox"]["max"], "f4")
        n = max(50, min(part_points, int(p.get("count", part_points))))
        chunks.append((rng.uniform(b_lo, b_hi, (n, 3)).astype("<f4"), k, KIND_RGB.get(p.get("kind"), (200, 160, 60))))
        parts_meta.append({
            "seq": k, "step": p["index"], "name": p["name"], "label": p.get("label", p["name"]),
            "kind": p.get("kind", "object"), "count": n, "start": start, "end": start + n, "bbox": p["bbox"],
        })
        start += n

    xyz = np.concatenate([c[0] for c in chunks])
    part = np.concatenate([np.full(len(c[0]), c[1], "<u2") for c in chunks])
    rgb = np.concatenate([np.tile(np.array(c[2], "u1"), (len(c[0]), 1)) for c in chunks])
    size_mm = np.full(len(xyz), 12, "u1")
    blob = b"".join(np.ascontiguousarray(a).tobytes() for a in (xyz, part, rgb, size_mm))

    floor = next((p for p in parts_meta if p["name"] == "floor"), None)
    floor_y = float(np.median(xyz[floor["start"]:floor["end"], 1])) if floor else float(lo[1])
    meta = {
        "version": 1,
        "fixture": True,
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {**manifest["source"], "file": f"FIXTURE ({manifest['source']['file']})"},
        "frame": manifest.get("frame", "fixture"), "units": manifest.get("units", "scene_units"),
        "up_axis": manifest.get("up_axis", "y"),
        "count": len(xyz), "pool_count": pool_points, "pool_total": pool_points, "removed_count": 0,
        "room_bounds": bounds, "floor_y": round(floor_y, 4), "dollhouse_cut_y": manifest.get("dollhouse_cut_y"),
        "layout": "float32 xyz[n*3] | uint16 part[n] | uint8 rgb[n*3] | uint8 size_mm[n]",
        "parts": parts_meta,
    }
    return blob, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--pool", type=int, default=20000, help="pool (unclaimed scan) points")
    ap.add_argument("--part-max", type=int, default=6000, help="points per part, at most")
    ap.add_argument("--force", action="store_true", help="replace a real export in --out")
    args = ap.parse_args()

    existing = args.out / "scene.json"
    if existing.exists() and not args.force and not orjson.loads(existing.read_bytes()).get("fixture"):
        print(f"{existing} is a real export; pass --force to replace it", file=sys.stderr)
        return 1

    blob, meta = build(orjson.loads(args.manifest.read_bytes()), args.pool, args.part_max)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "scene.bin").write_bytes(blob)
    (args.out / "scene.json").write_bytes(orjson.dumps(meta, option=orjson.OPT_INDENT_2) + b"\n")
    print(f"fixture: {meta['count']:,} points, {len(meta['parts'])} parts -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
