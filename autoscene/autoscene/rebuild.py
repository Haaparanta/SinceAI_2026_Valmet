"""Stage 8: the new room, built from the detected objects one at a time.

Order: floor, ceiling, walls (structure), then the detector's objects (most confident and biggest first), then the
geometric clusters. Every object gets a gravity-aligned oriented bounding box, its own SH0 PLY and a row in
scene.json; room.ply is the whole rebuilt room; leftovers.ply holds the kept splats no object claimed.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import orjson

from autoscene.lift import Instance
from autoscene.scene import STRUCTURE_NAMES, Scene
from autoscene.splats import write_sh0_ply

log = logging.getLogger("autoscene.rebuild")

# What the detector calls it -> what it is in a boiler room (the ceiling "beams" here are insulated pipes; there are
# no structural beams in the scan). Scores keep the detector's own words.
LABEL_ALIAS = {"beam": "insulated pipe", "duct": "insulated pipe"}


def obb_yup(p: np.ndarray) -> dict:
    """Gravity-aligned OBB: y stays up, yaw from PCA on the xz footprint, extents from the 2nd/98th percentiles
    (robust to floaters). Returns center, yaw_deg, extent (x', y, z'), R (3x3, columns = box axes), corners."""
    c = p.mean(0)
    xz = p[:, [0, 2]] - c[[0, 2]]
    if len(p) > 3:
        w, v = np.linalg.eigh(np.cov(xz.T))
        a = v[:, int(np.argmax(w))]
    else:
        a = np.array([1.0, 0.0])
    yaw = float(np.arctan2(a[1], a[0]))
    R = np.array([[np.cos(yaw), 0, -np.sin(yaw)], [0, 1, 0], [np.sin(yaw), 0, np.cos(yaw)]])
    q = (p - c) @ R
    lo, hi = np.percentile(q, 2, 0), np.percentile(q, 98, 0)
    center = c + R @ ((lo + hi) / 2)
    ext = hi - lo
    half = ext / 2
    corners = np.array([[sx * half[0], sy * half[1], sz * half[2]] for sx in (-1, 1) for sy in (-1, 1)
                        for sz in (-1, 1)]) @ R.T + center
    return {"center": [round(float(v), 4) for v in center], "yaw_deg": round(float(np.degrees(yaw)), 2),
            "extent": [round(float(v), 4) for v in ext], "R": [[round(float(v), 6) for v in row] for row in R],
            "corners": [[round(float(v), 4) for v in cc] for cc in corners]}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "object"


def structure_instances(sc: Scene, start_id: int) -> list[Instance]:
    out = []
    for code in range(1, 7):
        rows = np.flatnonzero(sc.keep & (sc.structure == code)).astype(np.int32)
        if len(rows) < 100:
            continue
        name = STRUCTURE_NAMES[code]
        out.append(Instance(start_id + len(out), rows, name.replace("_", " "), 1.0, {name: 1.0}, [], [],
                            "structure", {}))
    return out


def order_objects(sc: Scene, instances: list[Instance]) -> list[Instance]:
    """Structure first, then detector objects by confidence x size, then clusters by size."""
    struct = structure_instances(sc, 10_000)
    det = sorted((i for i in instances if i.source == "yoloe"), key=lambda i: -(i.confidence * np.log1p(i.n)))
    clu = sorted((i for i in instances if i.source == "cluster"), key=lambda i: -i.n)
    return struct + det + clu


def rebuild(sc: Scene, instances: list[Instance], out: Path) -> list[dict]:
    objects_dir = out / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    for old in objects_dir.glob("*.ply"):
        old.unlink()
    ordered = order_objects(sc, instances)
    rows: list[dict] = []
    counts: dict[str, int] = {}
    claimed = np.zeros(sc.n, dtype=bool)
    all_rows = []
    for k, ins in enumerate(ordered, start=1):
        ins.label = LABEL_ALIAS.get(ins.label, ins.label)
        base = slug(ins.label)
        counts[base] = counts.get(base, 0) + 1
        name = f"{k:03d}_{base}_{counts[base]}"
        rows_k = ins.splats[~claimed[ins.splats]]           # a splat belongs to the first object that took it
        if len(rows_k) < 50:
            continue
        claimed[rows_k] = True
        p = sc.xyz[rows_k]
        obb = obb_yup(p)
        aabb = {"min": [round(float(v), 4) for v in p.min(0)], "max": [round(float(v), 4) for v in p.max(0)]}
        write_sh0_ply(objects_dir / f"{name}.ply", sc.splats[rows_k], comment=f"autoscene object {name}")
        rows.append({
            "index": k, "name": name, "label": ins.label, "source": ins.source, "confidence": round(ins.confidence, 3),
            "n_splats": len(rows_k), "obb": obb, "aabb": aabb, "scores": ins.scores, "views": ins.views,
            "detections": ins.detections, "info": ins.info, "ply": f"objects/{name}.ply",
        })
        all_rows.append(rows_k)
    all_idx = np.concatenate(all_rows) if all_rows else np.zeros(0, np.int32)
    write_sh0_ply(out / "room.ply", sc.splats[all_idx], comment="autoscene rebuilt room (all objects)")
    leftovers = np.flatnonzero(sc.keep & ~claimed)
    write_sh0_ply(out / "leftovers.ply", sc.splats[leftovers], comment="autoscene: kept splats no object claimed")
    np.savez_compressed(out / "objects.npz", splats=all_idx, sizes=np.array([r["n_splats"] for r in rows]))
    by_label: dict[str, int] = {}
    for r in rows:
        by_label[r["label"]] = by_label.get(r["label"], 0) + 1
    scene = {
        "source": sc.source, "frame": "world-rotz180-v1 (autoscene.orientation)", "up_axis": "y",
        "units": "scene_units (about metres)", "n_objects": len(rows), "by_label": by_label,
        "by_source": {s: sum(1 for r in rows if r["source"] == s) for s in ("structure", "yoloe", "cluster")},
        "coverage": {"claimed": int(claimed.sum()), "kept": int(sc.keep.sum()), "leftovers": len(leftovers)},
        "floor_plane": list(sc.floor_plane), "ceiling_y": sc.ceiling_y, "walls": sc.walls,
        "room_bounds_p1_p99": {"min": sc.bmin.tolist(), "max": sc.bmax.tolist()},
        "objects": rows,
    }
    (out / "scene.json").write_bytes(orjson.dumps(scene, option=orjson.OPT_INDENT_2))
    log.info("rebuilt room: %d objects (%s), %s of %s kept splats claimed, %s leftovers", len(rows), by_label,
             f"{int(claimed.sum()):,}", f"{int(sc.keep.sum()):,}", f"{len(leftovers):,}")
    return rows
