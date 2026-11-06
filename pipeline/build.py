"""Step-by-step twin build: one proposal at a time, one image per step, a human decides every step.

State lives in build/ (manifest.json, parts/*.idx.npy, current.ply) and images/ (<index>_<YYYYMMDD-HHMMSS>.png).

    uv run python pipeline/build.py init      # empty current.ply + manifest, image of the scan as delivered
    uv run python pipeline/build.py status    # what is in the build so far
    uv run python pipeline/build.py preview --out FILE [--rgb] [--fill 0.25 --box xmin ymin zmin xmax ymax zmax]
                                              # render without touching state or images/ (camera checks)
    uv run python pipeline/build.py clean below_floor|behind_back_wall|floating_fog|outside_room [--set key=value]
                                              # propose a cleaning step: image with removed points red, kept grey
    uv run python pipeline/build.py part floor [--set key=value]
                                              # propose the next part: new part red, accepted parts grey,
                                              # points not built yet as a faint backdrop
    uv run python pipeline/build.py accept | reject [--note TEXT]
                                              # decide the pending proposal; the image gets an ACCEPTED/REJECTED badge;
                                              # an accepted part is written to build/parts/ and build/current.ply

The flipbook comes as a further subcommand.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import orjson
from common.orientation import FRAME
from common.ply_io import read_header
from PIL import Image
from stepbuild import render as R
from stepbuild import state as S
from stepbuild.cleaning import CLEANERS
from stepbuild.parts import DETECTORS
from stepbuild.splats import SH0_DTYPE, load_real_splats, rgb_of, size_of, write_sh0_ply, xyz_of

log = logging.getLogger("build")
DEFAULT_PLY = S.ROOT / "data" / "raw" / "Industrial Boiler Room (1).ply"
CACHE = S.ROOT / "data" / "derived" / f"real_sh0_{FRAME}.npy"


def _room_bounds(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.percentile(xyz, 1, axis=0), np.percentile(xyz, 99, axis=0)


def _save(im, index: int, when) -> Path:
    """images/<index>_<YYYYMMDD-HHMMSS>.png as a 256-colour palette PNG (~0.3 MB instead of ~1.1 MB; the renders are
    flat red/grey/true-colour dots, so the palette is visually lossless and 100+ images stay git-friendly)."""
    path = S.image_path(index, when)
    path.parent.mkdir(parents=True, exist_ok=True)
    _quantized(im).save(path, optimize=True)
    return path


def _quantized(im: Image.Image) -> Image.Image:
    return im.convert("RGB").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


def _stamp(image: str, text: str, rgb: tuple[int, int, int]) -> None:
    path = S.ROOT / image
    im = Image.open(path).convert("RGB")
    R.draw_badge(im, text, rgb)
    _quantized(im).save(path, optimize=True)


def _parse_params(pairs: list[str]) -> dict[str, float]:
    out = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key.strip()] = float(value)
    return out


def _bounds(m: S.Manifest) -> tuple[np.ndarray, np.ndarray]:
    """Fixed room bounds from init, so every overview/elevation image uses the same framing (flipbook)."""
    b = m.data["room_bounds_p1_p99"]
    return np.array(b["min"]), np.array(b["max"])


def _close_pending(m: S.Manifest, status: str, badge_rgb: tuple[int, int, int], note: str = "") -> dict:
    pending = orjson.loads(S.PENDING.read_bytes())
    step = m.step(pending["index"])
    step["status"] = status
    step["decided_at"] = S.now_local().isoformat(timespec="seconds")
    if note:
        step["note"] = note
    _stamp(step["image"], status.upper(), badge_rgb)
    return pending


def _check_pending(m: S.Manifest, replace: bool) -> bool:
    """False if a proposal is waiting and may not be replaced."""
    if S.PENDING.exists():
        if not replace:
            p = orjson.loads(S.PENDING.read_bytes())
            log.error("step %04d (%s) is still pending: accept / reject it first, or pass --replace", p["index"], p["name"])
            return False
        _close_pending(m, "replaced", R.REJECTED_RGB, "replaced by a new proposal")
        S.PENDING_IDX.unlink(missing_ok=True)
        S.PENDING.unlink()
    return True


def cmd_clean(args: argparse.Namespace) -> int:
    m = S.Manifest.load()
    if not _check_pending(m, args.replace):
        return 1
    params = _parse_params(args.set)
    splats = load_real_splats(args.ply, CACHE)
    pool_idx = np.flatnonzero(m.pool_mask()).astype(np.uint32)
    pool = splats[pool_idx]
    xyz, size = xyz_of(pool), size_of(pool)
    bmin, bmax = _bounds(m)
    prop = CLEANERS[args.name](xyz, bmin, bmax, pool=pool, **params)
    rm = prop.remove
    show = ~rm if prop.hide_kept is None else ~rm & ~prop.hide_kept
    rm_size = size[rm] if prop.removed_size is None else prop.removed_size
    frame = R.render([R.Layer(xyz[show], R.GREY, "kept", size[show]), R.Layer(xyz[rm], R.RED, "removed", rm_size)],
                     prop.camera, R.WIDTH, R.HEIGHT - R.BANNER_H)
    when = S.now_local()
    index = S.next_image_index()
    im = R.compose(frame, f"{index:04d} · CLEAN · {prop.title}", prop.subtitle,
                   [(R.RED, "removed by this step"), (R.GREY, "kept")], when, "PROPOSED", R.PROPOSED_RGB)
    path = _save(im, index, when)
    np.save(S.PENDING_IDX, pool_idx[rm])
    pending = {"index": index, "kind": "clean", "name": args.name, "params": prop.params, "info": prop.info,
               "count": int(rm.sum()), "pool_before": len(pool_idx), "indices": S.rel(S.PENDING_IDX),
               "image": S.rel(path)}
    S.PENDING.write_bytes(orjson.dumps(pending, option=orjson.OPT_INDENT_2) + b"\n")
    m.add_step(index=index, kind="clean", name=args.name, status="pending", image=S.rel(path),
               created_at=when.isoformat(timespec="seconds"), count=pending["count"],
               pool_before=pending["pool_before"], params=prop.params, info=prop.info, camera=prop.camera.to_dict(),
               visible_pixels=frame.counts)
    m.save()
    print(f"{index:04d} PROPOSED clean/{args.name}: remove {pending['count']:,} of {len(pool_idx):,} pool points")
    print(f"  {prop.subtitle}")
    print(f"  image {S.rel(path)}   -> `build.py accept` or `build.py reject`")
    return 0


def render_parts(splats: np.ndarray, m: S.Manifest, candidate: np.ndarray, context: np.ndarray, cam: R.Camera
                 ) -> R.Frame:
    """New part red over the accepted parts in grey (one z-buffer); the points not built yet drawn faint, only where
    no part covers the pixel, so they give orientation without hiding the build."""
    h = R.HEIGHT - R.BANNER_H
    built = splats[m.claimed_indices()]
    cand = splats[candidate]
    layers = [R.Layer(xyz_of(built), R.GREY, "accepted", size_of(built)),
              R.Layer(xyz_of(cand), R.RED, "new", size_of(cand))]
    front = R.render(layers, cam, R.WIDTH, h)
    ctx = splats[context]
    back = R.render([R.Layer(xyz_of(ctx), R.FAINT, "not built", 0.008, 1)], cam, R.WIDTH, h, edl_strength=0)
    covered = np.isfinite(front.depth)
    img = np.where(covered[..., None], front.image, back.image)
    counts = dict(front.counts)
    counts["not built"] = int((np.isfinite(back.depth) & ~covered).sum())
    return R.Frame(img, np.where(covered, front.depth, back.depth), cam, counts)


def cmd_part(args: argparse.Namespace) -> int:
    m = S.Manifest.load()
    if not _check_pending(m, args.replace):
        return 1
    params = _parse_params(args.set)
    splats = load_real_splats(args.ply, CACHE)
    pool_idx = np.flatnonzero(m.pool_mask()).astype(np.uint32)
    pool = splats[pool_idx]
    bmin, bmax = _bounds(m)
    prop = DETECTORS[args.name](xyz_of(pool), bmin, bmax, pool=pool, **params)
    take_idx = pool_idx[prop.take]
    frame = render_parts(splats, m, take_idx, pool_idx[~prop.take], prop.camera)
    when = S.now_local()
    index = S.next_image_index()
    n_parts = len(m.data["parts"])
    im = R.compose(frame, f"{index:04d} · PART {n_parts + 1} · {prop.title}", prop.subtitle,
                   [(R.RED, "new part"), (R.GREY, f"accepted ({n_parts})"), (R.FAINT, "not built yet")], when,
                   "PROPOSED", R.PROPOSED_RGB)
    path = _save(im, index, when)
    np.save(S.PENDING_IDX, take_idx)
    pts = xyz_of(splats[take_idx])
    bbox = {"min": [round(float(v), 4) for v in pts.min(0)], "max": [round(float(v), 4) for v in pts.max(0)]}
    pending = {"index": index, "kind": "part", "name": prop.name, "label": prop.label, "part_kind": prop.kind,
               "params": prop.params, "info": prop.info, "count": len(take_idx), "pool_before": len(pool_idx),
               "bbox": bbox, "indices": S.rel(S.PENDING_IDX), "image": S.rel(path)}
    S.PENDING.write_bytes(orjson.dumps(pending, option=orjson.OPT_INDENT_2) + b"\n")
    m.add_step(index=index, kind="part", name=prop.name, status="pending", image=S.rel(path),
               created_at=when.isoformat(timespec="seconds"), count=len(take_idx), pool_before=len(pool_idx),
               label=prop.label, part_kind=prop.kind, bbox=bbox, params=prop.params, info=prop.info,
               camera=prop.camera.to_dict(), visible_pixels=frame.counts)
    m.save()
    print(f"{index:04d} PROPOSED part/{prop.name}: {len(take_idx):,} of {len(pool_idx):,} pool points")
    print(f"  {prop.subtitle}")
    print(f"  image {S.rel(path)}   -> `build.py accept` or `build.py reject`")
    return 0


def write_current(splats: np.ndarray, m: S.Manifest) -> int:
    """build/current.ply = every accepted part, in the order accepted."""
    rows = splats[m.claimed_indices()]
    names = ", ".join(p["name"] for p in m.data["parts"]) or "empty"
    write_sh0_ply(S.CURRENT_PLY, rows, f"current state: {len(m.data['parts'])} parts ({names})")
    return len(rows)


def cmd_decide(args: argparse.Namespace) -> int:
    if not S.PENDING.exists():
        log.error("nothing pending")
        return 1
    m = S.Manifest.load()
    accept = args.cmd == "accept"
    pending = _close_pending(m, "accepted" if accept else "rejected",
                             R.ACCEPTED_RGB if accept else R.REJECTED_RGB, args.note)
    if accept and pending["kind"] == "clean":
        dest = S.REMOVED / f"{pending['index']:04d}_{pending['name']}.idx.npy"
        dest.parent.mkdir(parents=True, exist_ok=True)
        S.PENDING_IDX.replace(dest)
        m.data["removed"].append({"index": pending["index"], "name": pending["name"], "count": pending["count"],
                                  "params": pending["params"], "indices": S.rel(dest)})
    if accept and pending["kind"] == "part":
        stem = f"{pending['index']:04d}_{pending['name']}"
        dest = S.PARTS / f"{stem}.idx.npy"
        dest.parent.mkdir(parents=True, exist_ok=True)
        S.PENDING_IDX.replace(dest)
        splats = load_real_splats(args.ply, CACHE)
        ply = S.PARTS / f"{stem}.ply"
        write_sh0_ply(ply, splats[np.load(dest)], f"part {pending['label']} (step {pending['index']:04d})")
        m.data["parts"].append({"index": pending["index"], "name": pending["name"], "label": pending["label"],
                                "kind": pending["part_kind"], "count": pending["count"], "bbox": pending["bbox"],
                                "params": pending["params"], "indices": S.rel(dest), "ply": S.rel(ply)})
        n_current = write_current(splats, m)
        print(f"  wrote {S.rel(ply)} ({pending['count']:,} splats) and {S.rel(S.CURRENT_PLY)} ({n_current:,} splats)")
    S.PENDING_IDX.unlink(missing_ok=True)
    S.PENDING.unlink()
    m.save()
    pool = int(m.pool_mask().sum())
    print(f"{pending['index']:04d} {'ACCEPTED' if accept else 'REJECTED'} {pending['kind']}/{pending['name']}"
          f" · pool now {pool:,} points")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if S.MANIFEST.exists() and not args.force:
        log.error("%s exists; the build has started. Use --force to start over (old images stay).", S.rel(S.MANIFEST))
        return 1
    header_rows, _, _ = read_header(str(args.ply))
    splats = load_real_splats(args.ply, CACHE)
    m = S.Manifest.new(args.ply.name, header_rows, len(splats))
    write_sh0_ply(S.CURRENT_PLY, np.empty(0, dtype=SH0_DTYPE), "current state: empty")
    S.PARTS.mkdir(parents=True, exist_ok=True)

    xyz = xyz_of(splats)
    bmin, bmax = _room_bounds(xyz)
    cam = R.overview_camera(bmin, bmax)
    frame = R.render([R.Layer(xyz, rgb_of(splats), "scan", size_of(splats))], cam, R.WIDTH, R.HEIGHT - R.BANNER_H,
                     edl_strength=0.6)
    when = S.now_local()
    index = S.next_image_index()
    im = R.compose(
        frame,
        f"{index:04d} · START · the scan as delivered",
        f"{len(splats):,} real splats of {header_rows:,} header rows · true colour · build is empty (0 parts)",
        legend=[], when=when, badge="START",
    )
    path = _save(im, index, when)
    m.add_step(index=index, kind="start", name="scan", status="info", image=S.rel(path),
               created_at=when.isoformat(timespec="seconds"), points=len(splats), camera=cam.to_dict())
    m.data["room_bounds_p1_p99"] = {"min": [round(float(v), 4) for v in bmin],
                                    "max": [round(float(v), 4) for v in bmax]}
    m.save()
    log.info("build started: %s, %s (0 splats), image %s", S.rel(S.MANIFEST), S.rel(S.CURRENT_PLY), S.rel(path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not S.MANIFEST.exists():
        print("no build yet: run `uv run python pipeline/build.py init`")
        return 1
    m = S.Manifest.load()
    src = m.data["source"]
    pool = int(m.pool_mask().sum())
    print(f"source   {src['file']}: {src['real_rows']:,} real rows of {src['header_rows']:,}")
    print(f"removed  {len(m.data['removed'])} cleaning steps, {len(m.removed_indices()):,} rows")
    print(f"parts    {len(m.data['parts'])} accepted, {len(m.claimed_indices()):,} rows in current.ply")
    print(f"pool     {pool:,} rows not yet removed or claimed")
    for s in m.data["steps"]:
        print(f"  {s['index']:04d}  {s['kind']:<8} {s['name']:<24} {s['status']:<9} {s['image']}")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    splats = load_real_splats(args.ply, CACHE)
    xyz = xyz_of(splats)
    bmin, bmax = _room_bounds(xyz)
    size = size_of(splats)
    layers: list[R.Layer] = []
    if args.box:
        lo, hi = np.array(args.box[:3]), np.array(args.box[3:])
        inside = ((xyz >= lo) & (xyz <= hi)).all(1)
        cam = R.framing_camera(lo, hi, np.array(args.view), fill=args.fill)
        layers.append(R.Layer(xyz[~inside], R.GREY, "rest", size[~inside]))
        layers.append(R.Layer(xyz[inside], R.RED, "box", size[inside]))
    else:
        cam = R.overview_camera(bmin, bmax)
        layers.append(R.Layer(xyz, rgb_of(splats) if args.rgb else R.GREY, "scan", size))
    frame = R.render(layers, cam, R.WIDTH, R.HEIGHT - R.BANNER_H)
    if args.box:
        span = R.screen_span(R.box_corners(lo, hi), cam)
        frame.counts["box_span_w_h"] = [round(span[0], 3), round(span[1], 3)]  # type: ignore[assignment]
    im = R.compose(frame, "PREVIEW (not saved to images/)", str(frame.counts),
                   [(R.RED, "candidate"), (R.GREY, "accepted")], S.now_local())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    im.save(args.out)
    print(args.out, frame.counts)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ply", type=Path, default=DEFAULT_PLY, help="source 3DGS PLY (default data/raw/...)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="start an empty build and save the first image")
    p.add_argument("--force", action="store_true", help="overwrite build/manifest.json and current.ply")
    p.set_defaults(fn=cmd_init)
    sub.add_parser("status", help="print the build state").set_defaults(fn=cmd_status)
    p = sub.add_parser("preview", help="render to --out without touching the build")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rgb", action="store_true", help="true colour instead of grey (overview only)")
    p.add_argument("--box", type=float, nargs=6, metavar=("XMIN", "YMIN", "ZMIN", "XMAX", "YMAX", "ZMAX"))
    p.add_argument("--view", type=float, nargs=3, default=(0.0, -0.45, -1.0), help="view direction for --box")
    p.add_argument("--fill", type=float, default=0.25, help="share of the frame the box should span")
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("clean", help="propose a cleaning step (Step 2)")
    p.add_argument("name", choices=sorted(CLEANERS))
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="filter parameter, e.g. margin=0.05")
    p.add_argument("--replace", action="store_true", help="mark a pending proposal as replaced and propose again")
    p.set_defaults(fn=cmd_clean)
    p = sub.add_parser("part", help="propose the next part (Step 3+)")
    p.add_argument("name", choices=sorted(DETECTORS))
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="detector parameter")
    p.add_argument("--replace", action="store_true", help="mark a pending proposal as replaced and propose again")
    p.set_defaults(fn=cmd_part)
    for name in ("accept", "reject"):
        p = sub.add_parser(name, help=f"{name} the pending proposal")
        p.add_argument("--note", default="", help="why (kept in the manifest)")
        p.set_defaults(fn=cmd_decide)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.cmd not in ("status", "reject") and not args.ply.exists():
        log.error("PLY not found: %s", args.ply)
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
