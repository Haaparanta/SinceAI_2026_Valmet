"""Compare the manual build (human-approved reference) with the automatic build, part by part, from their boxes alone.

    uv run python scripts/compare_builds.py                 # -> data/derived/compare.json + docs/build_comparison.md
    uv run python scripts/compare_builds.py --no-report     # JSON only (the viewer reads it in ?scene=both)

Inputs are committed files, no .ply needed: build/manifest.json (manual parts, axis-aligned bboxes) and
autoscene/out/scene.json (automatic objects, `aabb`). Both are in the same frame (world-rotz180-v1) of the same scan.

Per manual part:
    best       the automatic object with the highest box IoU
    fragments  automatic objects lying at least half inside the part's box (padded by PAD), e.g. the pieces a pipe run
               was split into
    coverage   share of the part's box volume covered by the union of its fragments (voxelised)
    status     matched  best IoU >= 0.5
               split    >= 2 fragments covering >= 40 %
               partial  best IoU >= 0.2, or fragments covering >= 20 %
               missed   anything less
Per automatic object: `in` = the manual part it lies (at least half) inside, smallest such part first; null when the
automatic build found something the manual build does not have.

Box geometry only: a pipe's box holds air as well as pipe, so coverage is an upper bound on what the splats would say.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "build" / "manifest.json"
AUTOSCENE = ROOT / "autoscene" / "out" / "scene.json"
OUT = ROOT / "data" / "derived" / "compare.json"
REPORT = ROOT / "docs" / "build_comparison.md"

PAD = 0.05            # scene units added around a manual box before asking "is this automatic object inside it?"
INSIDE = 0.5          # share of an automatic box that must lie inside
MIN_THICK = 0.04      # thin boxes (floor, ceiling slabs) are thickened to this before IoU, so a few cm offset still counts
VOXEL = 0.02          # coverage grid step, scene units (at most MAX_CELLS cells per axis)
MAX_CELLS = 200
STATUSES = ("matched", "split", "partial", "missed")


def as_box(b: dict) -> np.ndarray:
    return np.array([b["min"], b["max"]], dtype=float)


def thicken(box: np.ndarray, t: float = MIN_THICK) -> np.ndarray:
    c = box.mean(0)
    half = np.maximum((box[1] - box[0]) / 2, t / 2)
    return np.array([c - half, c + half])


def vol(box: np.ndarray) -> float:
    return float(np.prod(np.clip(box[1] - box[0], 0, None)))


def inter(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.array([np.maximum(a[0], b[0]), np.minimum(a[1], b[1])])


def iou(a: np.ndarray, b: np.ndarray) -> float:
    a, b = thicken(a), thicken(b)
    i = vol(inter(a, b))
    u = vol(a) + vol(b) - i
    return i / u if u > 0 else 0.0


def inside_share(obj: np.ndarray, part: np.ndarray, pad: float = PAD) -> float:
    """Share of `obj`'s volume inside `part` grown by `pad`."""
    obj = thicken(obj)
    grown = np.array([part[0] - pad, part[1] + pad])
    v = vol(obj)
    return vol(inter(obj, grown)) / v if v > 0 else 0.0


def coverage(part: np.ndarray, frags: list[np.ndarray]) -> float:
    """Share of `part`'s (thickened) volume covered by the union of `frags`, on a voxel grid."""
    if not frags:
        return 0.0
    part = thicken(part)
    size = part[1] - part[0]
    n = np.clip(np.ceil(size / VOXEL).astype(int), 1, MAX_CELLS)
    axes = [part[0][k] + (np.arange(n[k]) + 0.5) * size[k] / n[k] for k in range(3)]
    covered = np.zeros(tuple(n), dtype=bool)
    for f in frags:
        f = thicken(f)
        sl = []
        for k in range(3):
            idx = np.flatnonzero((axes[k] >= f[0][k]) & (axes[k] <= f[1][k]))
            if not len(idx):
                break
            sl.append(slice(idx[0], idx[-1] + 1))
        else:
            covered[tuple(sl)] = True
    return float(covered.mean())


def same_class(obj: dict, part: dict) -> bool:
    return (obj["source"] == "structure") == (part.get("kind") == "structure")


def gap(a: np.ndarray, b: np.ndarray) -> float:
    """Distance between two boxes (0 when they touch or overlap)."""
    d = np.maximum(0, np.maximum(a[0] - b[1], b[0] - a[1]))
    return float(np.linalg.norm(d))


def dy(a: np.ndarray, b: np.ndarray) -> float:
    """Vertical offset of b's centre from a's (positive = b higher)."""
    return float(b.mean(0)[1] - a.mean(0)[1])


def status_of(best_iou: float, n_frags: int, cov: float) -> str:
    if best_iou >= 0.5:
        return "matched"
    if n_frags >= 2 and cov >= 0.4:
        return "split"
    if best_iou >= 0.2 or cov >= 0.2:
        return "partial"
    return "missed"


def compare(manual: dict, auto: dict) -> dict:
    parts = manual["parts"]
    objects = auto["objects"]
    pboxes = [as_box(p["bbox"]) for p in parts]
    oboxes = [as_box(o["aabb"]) for o in objects]

    rows = []
    for p, pb in zip(parts, pboxes, strict=True):
        ious = np.array([iou(pb, ob) for ob in oboxes])
        best = int(ious.argmax()) if len(ious) else -1
        # structures (floor, walls, ceiling) are pieces of structures only, objects of objects only: a pipe lying on the
        # floor is not a piece of the floor
        frag_idx = [i for i, ob in enumerate(oboxes)
                    if same_class(objects[i], p) and inside_share(ob, pb) >= INSIDE]
        cov = coverage(pb, [oboxes[i] for i in frag_idx])
        b_iou = float(ious[best]) if best >= 0 else 0.0
        if b_iou <= 0:
            best = -1
        # the closest automatic object of the same class, for "missed": often the same thing, offset or split differently
        same = [i for i in range(len(objects)) if same_class(objects[i], p) and i not in frag_idx]
        near = min(same, key=lambda i: (gap(pb, oboxes[i]), -ious[i]), default=-1)
        rows.append({
            "name": p["name"], "label": p.get("label", p["name"]), "kind": p.get("kind", "object"),
            "status": status_of(b_iou, len(frag_idx), cov),
            "best": {"name": objects[best]["name"], "label": objects[best]["label"], "iou": round(b_iou, 3)}
            if best >= 0 else None,
            "fragments": [objects[i]["name"] for i in sorted(frag_idx, key=lambda i: -vol(oboxes[i]))],
            "fragment_labels": dict(Counter(objects[i]["label"] for i in frag_idx).most_common()),
            "coverage": round(cov, 3),
            "nearest": {"name": objects[near]["name"], "label": objects[near]["label"],
                        "gap": round(gap(pb, oboxes[near]), 3), "dy": round(float(dy(pb, oboxes[near])), 3)}
            if near >= 0 else None,
        })

    # each automatic object -> the smallest manual part it lies inside (structures last: everything is "inside" the room)
    order = sorted(range(len(parts)), key=lambda k: (parts[k].get("kind") == "structure", vol(pboxes[k])))
    autos = []
    for o, ob in zip(objects, oboxes, strict=True):
        host = next((parts[k]["name"] for k in order if inside_share(ob, pboxes[k]) >= INSIDE
                     and (parts[k].get("kind") != "structure" or o["source"] == "structure")), None)
        autos.append({"name": o["name"], "label": o["label"], "source": o["source"], "in": host})

    counts = Counter(r["status"] for r in rows)
    found = [r for r in rows if r["status"] != "missed"]
    only = [a for a in autos if a["in"] is None]
    return {
        "version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inputs": {"manual": "build/manifest.json", "auto": "autoscene/out/scene.json",
                   "manual_parts": len(parts), "auto_objects": len(objects)},
        "params": {"pad": PAD, "inside": INSIDE, "min_thick": MIN_THICK, "voxel": VOXEL},
        "summary": {
            "status": {s: counts.get(s, 0) for s in STATUSES},
            "found": len(found),
            "found_share": round(len(found) / len(rows), 3) if rows else 0.0,
            "mean_best_iou": round(float(np.mean([r["best"]["iou"] if r["best"] else 0.0 for r in rows])), 3) if rows else 0.0,
            "auto_inside_manual": len(autos) - len(only),
            "auto_only": len(only),
            "auto_only_by_label": dict(Counter(a["label"] for a in only).most_common()),
        },
        "manual": rows,
        "auto": autos,
    }


def report(c: dict) -> str:
    s = c["summary"]
    st = s["status"]
    lines = [
        "# Manual vs automatic build",
        "",
        (f"Generated by `scripts/compare_builds.py` from `{c['inputs']['manual']}` ({c['inputs']['manual_parts']} parts) "
         f"and `{c['inputs']['auto']}` ({c['inputs']['auto_objects']} objects). Box geometry only (see the script's "
         "docstring)."),
        "The manual build is the human-approved reference; the viewer shows both at `?scene=both`.",
        "",
        "## Summary",
        "",
        (f"- **{s['found']} of {c['inputs']['manual_parts']}** manual parts are found by the automatic build "
         f"({round(100 * s['found_share'])} %): {st['matched']} matched, {st['split']} split into pieces, "
         f"{st['partial']} partial, {st['missed']} missed."),
        f"- Mean best box IoU: {s['mean_best_iou']:.2f}.",
        (f"- {s['auto_inside_manual']} automatic objects lie inside a manual part; **{s['auto_only']}** are things the "
         "manual build does not have yet."),
        "",
        "## Manual parts",
        "",
        "| Part | Kind | Status | Best automatic match (IoU) | Pieces inside | Coverage |",
        "|---|---|---|---|---:|---:|",
    ]
    for r in c["manual"]:
        best = f"{r['best']['label']} ({r['best']['iou']:.2f})" if r["best"] else "–"
        pieces = ", ".join(f"{n}× {lab}" for lab, n in r["fragment_labels"].items()) or "–"
        lines.append(f"| {r['label']} | {r['kind']} | {r['status']} | {best} | {len(r['fragments'])}: {pieces} | "
                     f"{round(100 * r['coverage'])} % |")
    missed = [r for r in c["manual"] if r["status"] == "missed" and r["nearest"]]
    if missed:
        lines += ["", "## Missed parts: the closest automatic object", ""]
        for r in missed:
            n = r["nearest"]
            lines.append(f"- **{r['label']}**: closest is `{n['name']}` ({n['label']}), {n['gap']:.2f} u away, its centre "
                         f"{abs(n['dy']):.2f} u {'higher' if n['dy'] > 0 else 'lower'}.")
    lines += ["", "## Automatic objects the manual build does not have", "", "| Label | Count |", "|---|---:|"]
    lines += [f"| {lab} | {n} |" for lab, n in s["auto_only_by_label"].items()]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manual", type=Path, default=MANIFEST)
    ap.add_argument("--auto", type=Path, default=AUTOSCENE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--report", type=Path, default=REPORT)
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()

    c = compare(orjson.loads(args.manual.read_bytes()), orjson.loads(args.auto.read_bytes()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(orjson.dumps(c, option=orjson.OPT_INDENT_2) + b"\n")
    if not args.no_report:
        args.report.write_text(report(c))
    s = c["summary"]
    print(f"found {s['found']}/{c['inputs']['manual_parts']} manual parts ({s['status']}), "
          f"{s['auto_only']} automatic-only objects -> {args.out}" + ("" if args.no_report else f" + {args.report}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
