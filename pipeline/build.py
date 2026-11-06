"""Step-by-step twin build: one proposal at a time, one image per step, a human decides every step.

State lives in build/ (manifest.json, parts/*.idx.npy, current.ply) and images/ (<index>_<YYYYMMDD-HHMMSS>.png).

    uv run python pipeline/build.py init      # empty current.ply + manifest, image of the scan as delivered
    uv run python pipeline/build.py status    # what is in the build so far
    uv run python pipeline/build.py preview --out FILE [--rgb] [--fill 0.25 --box xmin ymin zmin xmax ymax zmax]
                                              # render without touching state or images/ (camera checks)

Cleaning (Step 2), parts (Step 3+) and the flipbook come as further subcommands.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
from common.ply_io import read_header
from PIL import Image
from stepbuild import render as R
from stepbuild import state as S
from stepbuild.splats import SH0_DTYPE, load_real_splats, rgb_of, size_of, write_sh0_ply, xyz_of

log = logging.getLogger("build")
DEFAULT_PLY = S.ROOT / "data" / "raw" / "Industrial Boiler Room (1).ply"
CACHE = S.ROOT / "data" / "derived" / "real_sh0.npy"


def _room_bounds(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.percentile(xyz, 1, axis=0), np.percentile(xyz, 99, axis=0)


def _save(im, index: int, when) -> Path:
    """images/<index>_<YYYYMMDD-HHMMSS>.png as a 256-colour palette PNG (~0.3 MB instead of ~1.1 MB; the renders are
    flat red/grey/true-colour dots, so the palette is visually lossless and 100+ images stay git-friendly)."""
    path = S.image_path(index, when)
    path.parent.mkdir(parents=True, exist_ok=True)
    pal = im.convert("RGB").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal.save(path, optimize=True)
    return path


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
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.cmd != "status" and not args.ply.exists():
        log.error("PLY not found: %s", args.ply)
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
