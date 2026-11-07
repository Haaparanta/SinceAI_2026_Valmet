"""Synthetic stand-ins for the viewer exports, so the web viewer can be tested without the scan.

    uv run python scripts/make_viewer_fixture.py                 # both builds (refuses to replace a real export)
    uv run python scripts/make_viewer_fixture.py --build manual  # data/derived/viewer/ only
    uv run python scripts/make_viewer_fixture.py --build auto    # data/derived/viewer_auto/ only
    uv run python scripts/make_viewer_fixture.py --out /tmp/v    # anywhere else (<out>/viewer, <out>/viewer_auto)

The real exports (scripts/export_viewer_scene.py, scripts/export_autoscene_viewer.py) need the gitignored master .ply.
These write the same layout from committed files alone: the manual build from build/manifest.json, the automatic build
from autoscene/out/scene.json. Every part becomes a box of random points inside its bbox, the pool is a sparse haze
over the room bounds. Part names, labels, kinds, order and bboxes match the real builds, so URLs like `?part=pipe_3`
behave the same; colours and shapes do not. scene.json carries "fixture": true. scene.splat (the viewer's Splats mode)
holds the same rows as small round splats.
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
AUTOSCENE = ROOT / "autoscene" / "out" / "scene.json"
OUT = ROOT / "data" / "derived"
DIRS = {"manual": "viewer", "auto": "viewer_auto"}

KIND_RGB = {"structure": (120, 124, 132), "object": (60, 150, 220), "cluster": (150, 110, 200)}
AUTO_KIND = {"structure": "structure", "yoloe": "object", "cluster": "cluster"}  # as scripts/export_autoscene_viewer.py


def manual_parts(manifest: dict) -> list[dict]:
    return [{"step": p["index"], "name": p["name"], "label": p.get("label", p["name"]), "kind": p.get("kind", "object"),
             "count": p.get("count", 0), "bbox": p["bbox"]} for p in manifest["parts"]]


def auto_parts(scene: dict) -> list[dict]:
    return [{"step": o["index"], "name": o["name"], "label": o["label"], "kind": AUTO_KIND.get(o["source"], "object"),
             "source": o["source"], "confidence": o["confidence"], "count": o.get("n_splats", 0), "bbox": o["aabb"],
             "images": []} for o in scene["objects"]]


def build(parts: list[dict], bounds: dict, pool_points: int, part_points: int, seed: int = 0) -> tuple[bytes, dict, bytes]:
    rng = np.random.default_rng(seed)
    lo, hi = np.array(bounds["min"], "f4"), np.array(bounds["max"], "f4")

    chunks = [(rng.uniform(lo, hi, (pool_points, 3)).astype("<f4"), 0, (70, 70, 80))]
    parts_meta, start = [], pool_points
    for k, p in enumerate(parts, 1):
        b_lo, b_hi = np.array(p["bbox"]["min"], "f4"), np.array(p["bbox"]["max"], "f4")
        n = max(50, min(part_points, int(p["count"] or part_points)))
        chunks.append((rng.uniform(b_lo, b_hi, (n, 3)).astype("<f4"), k, KIND_RGB.get(p["kind"], (200, 160, 60))))
        parts_meta.append({"seq": k, **{key: v for key, v in p.items() if key not in ("count", "bbox")},
                           "count": n, "start": start, "end": start + n, "bbox": p["bbox"]})
        start += n

    xyz = np.concatenate([c[0] for c in chunks])
    part = np.concatenate([np.full(len(c[0]), c[1], "<u2") for c in chunks])
    rgb = np.concatenate([np.tile(np.array(c[2], "u1"), (len(c[0]), 1)) for c in chunks])
    size_mm = np.full(len(xyz), 12, "u1")
    blob = b"".join(np.ascontiguousarray(a).tobytes() for a in (xyz, part, rgb, size_mm))
    splat = splat_rows(xyz, rgb)

    floor = next((p for p in parts_meta if p["name"] in ("floor", "001_floor_1")), None)
    floor_y = float(np.median(xyz[floor["start"]:floor["end"], 1])) if floor else float(lo[1])
    meta = {
        "version": 1,
        "fixture": True,
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(xyz), "pool_count": pool_points, "pool_total": pool_points, "removed_count": 0,
        "room_bounds": bounds, "floor_y": round(floor_y, 4),
        "layout": "float32 xyz[n*3] | uint16 part[n] | uint8 rgb[n*3] | uint8 size_mm[n]",
        "parts": parts_meta,
    }
    return blob, meta, splat


def splat_rows(xyz: np.ndarray, rgb: np.ndarray, scale: float = 0.012) -> bytes:
    """scripts/splat_format.py layout, 32 bytes: xyz f32 | scale xyz f32 | rgba u8 | quaternion wxyz u8 (identity)."""
    n = len(xyz)
    out = np.empty((n, 32), np.uint8)
    out[:, 0:12] = xyz.astype("<f4").view(np.uint8).reshape(n, 12)
    out[:, 12:24] = np.full((n, 3), scale, "<f4").view(np.uint8).reshape(n, 12)
    out[:, 24:27] = rgb
    out[:, 27] = 255
    out[:, 28:32] = (255, 128, 128, 128)
    return out.tobytes()


def fixture(which: str, pool_points: int, part_points: int) -> tuple[bytes, dict, bytes]:
    if which == "manual":
        m = orjson.loads(MANIFEST.read_bytes())
        blob, meta, splat = build(manual_parts(m), m["room_bounds_p1_p99"], pool_points, part_points)
        meta.update(source={**m["source"], "file": f"FIXTURE ({m['source']['file']})"}, frame=m.get("frame", "fixture"),
                    units=m.get("units", "scene_units"), up_axis=m.get("up_axis", "y"),
                    dollhouse_cut_y=m.get("dollhouse_cut_y"))
    else:
        a = orjson.loads(AUTOSCENE.read_bytes())
        blob, meta, splat = build(auto_parts(a), a["room_bounds_p1_p99"], pool_points, max(50, part_points // 4), seed=1)
        meta.update(build="autoscene", source={"file": f"FIXTURE ({a['source']})", "header_rows": 0, "real_rows": 0},
                    frame=a.get("frame", "fixture"), units=a["units"], up_axis="y",
                    dollhouse_cut_y=round(float(a["ceiling_y"]) - 0.75, 3),
                    by_label=a["by_label"], by_source=a["by_source"])
    return blob, meta, splat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", choices=["manual", "auto", "all"], default="all")
    ap.add_argument("--out", type=Path, default=OUT, help="parent of viewer/ and viewer_auto/")
    ap.add_argument("--pool", type=int, default=20000, help="pool (unclaimed scan) points")
    ap.add_argument("--part-max", type=int, default=6000, help="points per part, at most")
    ap.add_argument("--force", action="store_true", help="replace a real export")
    ap.add_argument("--missing-only", action="store_true",
                    help="only write builds that have no scene.json yet (make test-web), never an error for real ones")
    args = ap.parse_args()

    status = 0
    for which in (["manual", "auto"] if args.build == "all" else [args.build]):
        out = args.out / DIRS[which]
        existing = out / "scene.json"
        if existing.exists() and args.missing_only:
            continue
        if existing.exists() and not args.force and not orjson.loads(existing.read_bytes()).get("fixture"):
            print(f"{existing} is a real export; pass --force to replace it", file=sys.stderr)
            status = 1
            continue
        blob, meta, splat = fixture(which, args.pool, args.part_max)
        out.mkdir(parents=True, exist_ok=True)
        (out / "scene.bin").write_bytes(blob)
        (out / "scene.splat").write_bytes(splat)
        (out / "scene.json").write_bytes(orjson.dumps(meta, option=orjson.OPT_INDENT_2) + b"\n")
        print(f"fixture ({which}): {meta['count']:,} points, {len(meta['parts'])} parts -> {out}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
