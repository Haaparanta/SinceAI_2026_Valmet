"""Step-by-step twin build: one proposal at a time, one image per step, a human decides every step.

State lives in build/ (manifest.json, parts/*.idx.npy, current.ply) and images/ (<index>_<YYYYMMDD-HHMMSS>.png).

    uv run python pipeline/build.py init      # empty current.ply + manifest, image of the scan as delivered
    uv run python pipeline/build.py status    # what is in the build so far
    uv run python pipeline/build.py restart --reason TEXT
                                              # reject what is pending, archive the run under build/archive/,
                                              # start a new empty build; image numbering continues
    uv run python pipeline/build.py preview --out FILE [--rgb] [--fill 0.25 --box xmin ymin zmin xmax ymax zmax]
                                              # render without touching state or images/ (camera checks)
    uv run python pipeline/build.py clean below_floor|behind_back_wall|floating_fog|outside_room [--set key=value]
                                              # propose a cleaning step: image with removed points red, kept grey
    uv run python pipeline/build.py part floor|ceiling|lamp [--set key=value]
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
from PIL import Image, ImageDraw
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


SEL_ALPHA, BUILT_ALPHA, REST_ALPHA = 0.8, 0.2, 0.08       # selection / accepted parts / everything else
FAILED_RGB = (231, 76, 60)


def _highlight(kind: str) -> tuple[tuple[int, int, int], str]:
    """Removed points are tinted red, added points green."""
    return (R.REMOVE_RGB, "removed") if kind == "clean" else (R.ADD_RGB, "added")


def _legend(kind: str) -> list[tuple[tuple[int, int, int], str]]:
    rgb, word = _highlight(kind)
    return [(rgb, f"{word} (80 %)"), ((150, 150, 150), "built 20 %"), ((75, 75, 80), "rest 8 %")]


def _step_images(m: S.Manifest) -> list[str]:
    return [img for s in m.data["steps"] for img in s.get("images", [s.get("image")]) if img]


def _close_pending(m: S.Manifest, status: str, badge_rgb: tuple[int, int, int], note: str = "") -> dict:
    pending = orjson.loads(S.PENDING.read_bytes())
    step = m.step(pending["index"])
    step["status"] = status
    step["decided_at"] = S.now_local().isoformat(timespec="seconds")
    if note:
        step["note"] = note
    for image in step.get("images", [step.get("image")]):
        _stamp(image, status.upper(), badge_rgb)
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


def _closeup_camera(pts: np.ndarray, view_dir: tuple[float, float, float] = (0.0, -0.35, -1.0)) -> R.Camera:
    """Close-up of the selection: its p2..p98 box from the open front side, slightly above. An object fills ~30 % of
    the frame (context stays visible); a room-scale selection (> 2 u) fills ~80 %."""
    lo, hi = np.percentile(pts, 2, axis=0), np.percentile(pts, 98, axis=0)
    fill = 0.3 if float(np.max(hi - lo)) < 2.0 else 0.8
    return R.framing_camera(lo, hi, np.array(view_dir), fill=fill)


def _layers(splats: np.ndarray, built_idx: np.ndarray, sel_idx: np.ndarray, rest_idx: np.ndarray, kind: str,
            alphas: tuple[float, float, float] = (SEL_ALPHA, BUILT_ALPHA, REST_ALPHA)) -> list[R.BlendLayer]:
    built, sel, rest = splats[built_idx], splats[sel_idx], splats[rest_idx]
    hl, _ = _highlight(kind)
    return [R.BlendLayer(xyz_of(rest), rgb_of(rest), alphas[2], "rest", size_of(rest)),
            R.BlendLayer(xyz_of(built), rgb_of(built), alphas[1], "built", size_of(built)),
            R.BlendLayer(xyz_of(sel), R.tint(rgb_of(sel), hl), alphas[0], "selected", np.maximum(size_of(sel), 0.01))]


def _render_views(splats: np.ndarray, m: S.Manifest, sel_idx: np.ndarray, rest_idx: np.ndarray,
                  views: list[tuple[str, R.Camera, np.ndarray | None]], kind: str) -> list[tuple[str, R.Frame]]:
    """Each view in true colours with the change tinted (red = removed, green = added) at 80 %, accepted parts
    20 %, the rest 8 % (optionally minus a per-view hide mask over rest_idx). The close-up also gets a box around
    the change."""
    built_idx = m.claimed_indices()
    hl, _ = _highlight(kind)
    out = []
    for name, cam, hide in views:
        rest = rest_idx if hide is None else rest_idx[~hide]
        frame = R.render_blend(_layers(splats, built_idx, sel_idx, rest, kind), cam)
        if name == "close-up" and len(sel_idx):
            pts = xyz_of(splats[sel_idx])
            lo, hi = np.percentile(pts, 2, axis=0), np.percentile(pts, 98, axis=0)
            h, w = frame.image.shape[:2]
            R.draw_box(frame.image, R.project_rect(R.box_corners(lo, hi), cam, w, h), hl)
        out.append((name, frame))
    return out


def _before_after(splats: np.ndarray, m: S.Manifest, sel_idx: np.ndarray, rest_idx: np.ndarray, kind: str
                  ) -> R.Frame:
    """BEFORE | AFTER from the outside camera, side by side. Clean step: before = all points (the ones to remove
    tinted red), after = without them. Part step: before = what is built, after = built + the new part (green)."""
    bmin, bmax = _bounds(m)
    hw, h = R.WIDTH // 2, R.HEIGHT - R.BANNER_H
    cam = R.outside_camera(bmin, bmax, width=hw, height=h)
    built = m.claimed_indices()
    none = np.empty(0, np.uint32)
    if kind == "clean":
        before = _layers(splats, built, sel_idx, rest_idx, kind, (SEL_ALPHA, 0.35, 0.25))
        after = _layers(splats, built, none, rest_idx, kind, (SEL_ALPHA, 0.35, 0.25))
    else:
        before = _layers(splats, built, none, np.concatenate([sel_idx, rest_idx]), kind, (SEL_ALPHA, SEL_ALPHA, 0.06))
        after = _layers(splats, built, sel_idx, rest_idx, kind, (SEL_ALPHA, SEL_ALPHA, 0.06))
    halves = [R.render_blend(before, cam, hw, h).image, R.render_blend(after, cam, hw, h).image]
    img = np.concatenate(halves, axis=1)
    img[:, hw - 1:hw + 1] = (90, 92, 100)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    for i, word in enumerate(("BEFORE", "AFTER")):
        d.text((i * hw + 16, h - 44), word, fill=(240, 240, 245), font=R._font(28))
    return R.Frame(np.asarray(im), np.full((h, R.WIDTH), np.inf, np.float32), cam, {})


def _object_pair(splats: np.ndarray, m: S.Manifest, sel_idx: np.ndarray, rest_idx: np.ndarray, kind: str
                 ) -> R.Frame:
    """Small parts: the same close-up twice side by side, from the middle of the room looking at the object (the
    style of image 0100: the room faint around it). Left: the object tinted green at 80 %. Right: the object in its
    own colours at 100 %."""
    bmin, bmax = _bounds(m)
    pts = xyz_of(splats[sel_idx])
    lo, hi = np.percentile(pts, 2, axis=0), np.percentile(pts, 98, axis=0)
    hw, h = R.WIDTH // 2, R.HEIGHT - R.BANNER_H
    cam = R.from_room_middle_camera(lo, hi, bmin, bmax, width=hw, height=h)
    built_idx = m.claimed_indices()
    left = _layers(splats, built_idx, sel_idx, rest_idx, kind)
    right = _layers(splats, built_idx, sel_idx, rest_idx, kind)
    sel = splats[sel_idx]
    right[-1] = R.BlendLayer(xyz_of(sel), rgb_of(sel), 1.0, "selected", np.maximum(size_of(sel), 0.01))
    img = np.concatenate([R.render_blend(left, cam, hw, h).image, R.render_blend(right, cam, hw, h).image], axis=1)
    img[:, hw - 1:hw + 1] = (90, 92, 100)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    hl, word = _highlight(kind)
    d.text((16, h - 44), f"{word.upper()}: GREEN", fill=hl, font=R._font(26))
    d.text((hw + 16, h - 44), "OWN COLOURS", fill=(240, 240, 245), font=R._font(26))
    return R.Frame(np.asarray(im), np.full((h, R.WIDTH), np.inf, np.float32), cam, {})


def _save_views(frames: list[tuple[str, R.Frame]], title: str, subtitle: str, badge: str,
                badge_rgb: tuple[int, int, int], kind: str, headline: str = "") -> list[str]:
    """One image per view, each with its own index: '<index> · <title>' and '<view> · <subtitle>', the headline
    (what changes, in plain words) on top of every picture."""
    paths = []
    hl, _ = _highlight(kind)
    for view, frame in frames:
        when = S.now_local()
        index = S.next_image_index()
        im = R.compose(frame, f"{index:04d} · {title}", f"{view} · {subtitle}", _legend(kind), when, badge,
                       badge_rgb, headline=headline, headline_rgb=hl)
        paths.append(S.rel(_save(im, index, when)))
    return paths


def _fail(m: S.Manifest, splats: np.ndarray, pool_idx: np.ndarray, kind: str, name: str, reason: str) -> int:
    """A failed step still gets an image (outside view of the current state), a FAILED badge and the reason."""
    bmin, bmax = _bounds(m)
    frames = _render_views(splats, m, np.empty(0, np.uint32), pool_idx,
                           [("outside, all points", R.outside_camera(bmin, bmax), None)], kind)
    images = _save_views(frames, f"{kind.upper()} · {name}", f"FAILED: {reason}", "FAILED", FAILED_RGB, kind,
                         headline=f"FAILED · no change · {reason}")
    m.add_step(index=int(Path(images[0]).name[:4]), kind=kind, name=name, status="failed", images=images,
               created_at=S.now_local().isoformat(timespec="seconds"), note=reason)
    m.save()
    print(f"FAILED {kind}/{name}: {reason}\n  image {images[0]}")
    return 1


def _propose(m: S.Manifest, splats: np.ndarray, pool_idx: np.ndarray, sel_mask: np.ndarray, *, kind: str,
             name: str, title: str, subtitle: str, extra: tuple[str, R.Camera, np.ndarray | None] | None,
             record: dict, headline: str, view_dir: tuple[float, float, float] = (0.0, -0.35, -1.0)) -> int:
    sel_idx = pool_idx[sel_mask]
    if len(sel_idx) == 0:
        return _fail(m, splats, pool_idx, kind, name, "the detector selected no points")
    bmin, bmax = _bounds(m)
    views = [("close-up", _closeup_camera(xyz_of(splats[sel_idx]), view_dir), None),
             ("outside, all points", R.outside_camera(bmin, bmax), None)]
    if extra is not None:
        views.append(extra)
    frames = _render_views(splats, m, sel_idx, pool_idx[~sel_mask], views, kind)
    frames.append(("before | after", _before_after(splats, m, sel_idx, pool_idx[~sel_mask], kind)))
    lo, hi = np.percentile(pts_all := xyz_of(splats[sel_idx]), 2, axis=0), np.percentile(pts_all, 98, axis=0)
    if kind == "part" and float(np.max(hi - lo)) < 2.0:          # small part: green | colour pair comes first
        frames.insert(0, ("close-up from the room, green | own colours",
                          _object_pair(splats, m, sel_idx, pool_idx[~sel_mask], kind)))
    images = _save_views(frames, title, subtitle, "PROPOSED", R.PROPOSED_RGB, kind, headline)
    index = int(Path(images[0]).name[:4])
    np.save(S.PENDING_IDX, sel_idx)
    pts = xyz_of(splats[sel_idx])
    bbox = {"min": [round(float(v), 4) for v in pts.min(0)], "max": [round(float(v), 4) for v in pts.max(0)]}
    pending = {"index": index, "kind": kind, "name": name, "count": len(sel_idx), "pool_before": len(pool_idx),
               "bbox": bbox, "indices": S.rel(S.PENDING_IDX), "images": images, **record}
    S.PENDING.write_bytes(orjson.dumps(pending, option=orjson.OPT_INDENT_2) + b"\n")
    m.add_step(index=index, kind=kind, name=name, status="pending", images=images,
               created_at=S.now_local().isoformat(timespec="seconds"), count=len(sel_idx), pool_before=len(pool_idx),
               bbox=bbox, headline=headline, cameras={v: f.camera.to_dict() for v, f in frames},
               layer_share={v: f.counts for v, f in frames}, **record)
    m.save()
    print(f"{index:04d} PROPOSED {kind}/{name}: {len(sel_idx):,} of {len(pool_idx):,} pool points")
    print(f"  {subtitle}")
    for img in images:
        print(f"  image {img}")
    print("  -> `build.py accept` or `build.py reject`")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    m = S.Manifest.load()
    if not _check_pending(m, args.replace):
        return 1
    splats = load_real_splats(args.ply, CACHE)
    pool_idx = np.flatnonzero(m.pool_mask()).astype(np.uint32)
    pool = splats[pool_idx]
    bmin, bmax = _bounds(m)
    try:
        prop = CLEANERS[args.name](xyz_of(pool), bmin, bmax, pool=pool, **_parse_params(args.set))
    except Exception as exc:  # noqa: BLE001 - a failed detector is a step outcome, shown as an image
        return _fail(m, splats, pool_idx, "clean", args.name, f"{type(exc).__name__}: {exc}")
    rm = prop.remove
    hide = None if prop.hide_kept is None else prop.hide_kept[~rm]
    n_clean = len(m.data["removed"]) + 1                  # numbered by accepted cleanings: drafts do not count
    return _propose(m, splats, pool_idx, rm, kind="clean", name=args.name,
                    title=f"CLEAN {n_clean} · {prop.title}", subtitle=prop.subtitle,
                    extra=("diagnostic view", prop.camera, hide),
                    record={"params": prop.params, "info": prop.info},
                    headline=f"REMOVE {int(rm.sum()):,} points ({100 * rm.mean():.1f} %) · {prop.what}")


def cmd_part(args: argparse.Namespace) -> int:
    m = S.Manifest.load()
    if not _check_pending(m, args.replace):
        return 1
    splats = load_real_splats(args.ply, CACHE)
    pool_idx = np.flatnonzero(m.pool_mask()).astype(np.uint32)
    pool = splats[pool_idx]
    bmin, bmax = _bounds(m)
    try:
        extra = {"number": 1 + sum(1 for p_ in m.data["parts"] if p_["name"].startswith(f"{args.name}_"))} \
            if args.name in ("lamp",) else {}
        prop = DETECTORS[args.name](xyz_of(pool), bmin, bmax, pool=pool, **extra, **_parse_params(args.set))
    except Exception as exc:  # noqa: BLE001
        return _fail(m, splats, pool_idx, "part", args.name, f"{type(exc).__name__}: {exc}")
    n_parts = len(m.data["parts"])
    return _propose(m, splats, pool_idx, prop.take, kind="part", name=prop.name,
                    title=f"PART {n_parts + 1} · {prop.title}", subtitle=prop.subtitle,
                    extra=("overview", prop.camera, None),
                    record={"label": prop.label, "part_kind": prop.kind, "params": prop.params, "info": prop.info},
                    headline=f"ADD {prop.label.upper()} · {int(prop.take.sum()):,} points as part {n_parts + 1}",
                    view_dir=prop.view_dir)


def write_current(splats: np.ndarray, m: S.Manifest) -> int:
    """build/current.ply = every accepted part, in the order accepted."""
    rows = splats[m.claimed_indices()]
    names = ", ".join(p["name"] for p in m.data["parts"]) or "empty"
    write_sh0_ply(S.CURRENT_PLY, rows, f"current state: {len(m.data['parts'])} parts ({names})")
    return len(rows)


STATE_RGB = (90, 160, 255)


def state_images(splats: np.ndarray, m: S.Manifest, event: str) -> list[str]:
    """Progress pictures after a decision, everything at 100 % opacity in true colour (nearest point wins):
    the whole kept scan (built parts + pool) from the fixed outside camera and from the START front camera, and
    once parts exist the built 3D world (current.ply) alone from outside. Recorded as a 'state' step."""
    bmin, bmax = _bounds(m)
    built = m.claimed_indices()
    kept = np.concatenate([built, np.flatnonzero(m.pool_mask()).astype(np.uint32)])
    start_cam = R.Camera(**{k: tuple(v) if isinstance(v, list) else v
                            for k, v in m.data["steps"][0]["camera"].items()}) if "camera" in m.data["steps"][0] \
        else R.overview_camera(bmin, bmax)
    n_parts, n_clean = len(m.data["parts"]), len(m.data["removed"])
    facts = f"{len(kept):,} points kept · {n_clean} cleanings · {n_parts} parts ({len(built):,} points in current.ply)"
    views = [("kept scan, outside", R.outside_camera(bmin, bmax), kept),
             ("kept scan, front (START camera)", start_cam, kept)]
    if len(built):
        views.append(("built 3D world = current.ply, outside", R.outside_camera(bmin, bmax), built))
    images = []
    for view, cam, idx in views:
        sub = splats[idx]
        frame = R.render([R.Layer(xyz_of(sub), rgb_of(sub), view, size_of(sub))], cam, R.WIDTH, R.HEIGHT - R.BANNER_H,
                         edl_strength=0.5)
        when = S.now_local()
        index = S.next_image_index()
        im = R.compose(frame, f"{index:04d} · STATE · {event}", f"{view} · 100 % · {facts}", [], when, "STATE",
                       STATE_RGB)
        images.append(S.rel(_save(im, index, when)))
    m.add_step(index=int(Path(images[0]).name[:4]), kind="state", name="progress", status="info", images=images,
               created_at=S.now_local().isoformat(timespec="seconds"), event=event, kept=len(kept),
               built=len(built))
    return images


PROBE_RGB = (190, 120, 255)


def cmd_probe(args: argparse.Namespace) -> int:
    """Pictures that help the user pick a level, saved in images/ like every step (no state change): for each
    --levels value, from the middle of the room looking straight up, the points at or above that level as green dots
    and everything else in true colour at 100 % (once with nearest-point-wins, once with the green on top); then one
    side view with every level drawn as a line."""
    m = S.Manifest.load()
    splats = load_real_splats(args.ply, CACHE)
    pool_idx = np.flatnonzero(m.pool_mask()).astype(np.uint32)
    kept = np.concatenate([m.claimed_indices(), pool_idx])
    pts, rgb = xyz_of(splats[kept]), rgb_of(splats[kept])
    size = size_of(splats[kept])
    bmin, bmax = _bounds(m)
    lamp = (rgb.min(1) >= args.white) & (pts[:, 1] >= min(args.levels) - 0.2)
    floor_y = next((p_["params"] for p_ in m.data["parts"] if p_["name"] == "floor"), None)
    eye_y = float(np.percentile(pts[:, 1], 1)) + 0.9 if floor_y is None else -1.07 + 0.9
    cam = R.look_up_from_middle(bmin, bmax, eye_y)
    h = R.HEIGHT - R.BANNER_H
    images = []

    def save(frame: R.Frame, title: str, sub: str, headline: str) -> None:
        when = S.now_local()
        index = S.next_image_index()
        im = R.compose(frame, f"{index:04d} · PROBE · {title}", sub, [(R.ADD_RGB, "at or above the level"),
                       ((200, 200, 200), "everything else, true colour")], when, "PROBE", PROBE_RGB,
                       headline=headline, headline_rgb=R.ADD_RGB)
        images.append(S.rel(_save(im, index, when)))

    for level in args.levels:
        sel = (pts[:, 1] >= level) & ~lamp
        n = int(sel.sum())
        rest = R.Layer(pts[~sel], rgb[~sel], "rest", size[~sel])
        green = R.Layer(pts[sel], np.broadcast_to(np.asarray(R.ADD_RGB, np.uint8), (n, 3)).copy(), "level",
                        np.maximum(size[sel], 0.015))
        honest = R.render([rest, green], cam, R.WIDTH, h, edl_strength=0.4)
        save(honest, f"ceiling level y >= {level:+.2f}, looking up", f"from the middle of the room, eye y {eye_y:+.2f}"
             f" · nearer points hide farther ones · {n:,} green points (lamps excluded)",
             f"LEVEL y >= {level:+.2f} · {n:,} green points · seen from below")
        back = R.render([rest], cam, R.WIDTH, h, edl_strength=0.4)
        front = R.render([green], cam, R.WIDTH, h, edl_strength=0)
        on_top = np.where(np.isfinite(front.depth)[..., None], front.image, back.image)
        save(R.Frame(on_top, back.depth, cam, {}), f"ceiling level y >= {level:+.2f}, green on top",
             f"same view, green drawn over everything · {n:,} green points", f"LEVEL y >= {level:+.2f} · green on top")
    labels = [args.labels[i] if i < len(args.labels) else "" for i in range(len(args.levels))]
    chart = R.level_chart(pts, rgb, list(zip(args.levels, labels)), args.y_lo, args.y_hi)
    save(R.Frame(chart, np.full(chart.shape[:2], np.inf, np.float32), cam, {}), "levels, side view",
         f"x across, height up (stretched {args.y_lo:+.1f}…{args.y_hi:+.1f}) · colour = the points' own · right: points"
         " per height", "WHICH LEVEL IS THE CEILING? · side view")
    m.add_step(index=int(Path(images[0]).name[:4]), kind="probe", name="ceiling_levels", status="info",
               images=images, created_at=S.now_local().isoformat(timespec="seconds"),
               levels=list(args.levels), labels=labels, camera=cam.to_dict())
    m.save()
    for img in images:
        print(f"  probe image {img}")
    return 0


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
    word = "ACCEPTED" if accept else "REJECTED"
    print(f"{pending['index']:04d} {word} {pending['kind']}/{pending['name']} · pool now {pool:,} points")
    images = state_images(load_real_splats(args.ply, CACHE), m,
                          f"after {pending['index']:04d} {word} ({pending['kind']} {pending['name']})")
    m.save()
    for img in images:
        print(f"  state image {img}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if S.MANIFEST.exists() and not args.force:
        log.error("%s exists; the build has started. Use --force to start over (old images stay).", S.rel(S.MANIFEST))
        return 1
    header_rows, _, _ = read_header(str(args.ply))
    splats = load_real_splats(args.ply, CACHE)
    m = S.Manifest.new(args.ply.name, header_rows, len(splats))
    m.data["frame"] = FRAME
    if getattr(args, "previous", None):
        m.data["previous_runs"] = args.previous
    write_sh0_ply(S.CURRENT_PLY, np.empty(0, dtype=SH0_DTYPE), "current state: empty")
    S.PARTS.mkdir(parents=True, exist_ok=True)

    xyz = xyz_of(splats)
    bmin, bmax = _room_bounds(xyz)
    cam = R.overview_camera(bmin, bmax)
    frame = R.render([R.Layer(xyz, rgb_of(splats), "scan", size_of(splats))], cam, R.WIDTH, R.HEIGHT - R.BANNER_H,
                     edl_strength=0.6)
    when = S.now_local()
    index = S.next_image_index()
    restart = " (restart)" if getattr(args, "previous", None) else ""
    im = R.compose(
        frame,
        f"{index:04d} · START{restart} · the scan, right way up",
        f"{len(splats):,} real splats of {header_rows:,} header rows · true colour · y up, floor at the bottom · "
        "build is empty (0 parts)",
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


def cmd_restart(args: argparse.Namespace) -> int:
    """Close the current run and start a new one. Nothing is deleted: the pending proposal is rejected (its image
    gets the badge), manifest + removed/ + parts/ move to build/archive/<time>_<reason>/, images stay in images/ and
    the new run's image numbers continue after them."""
    if not S.MANIFEST.exists():
        log.error("no build to restart; use init")
        return 1
    m = S.Manifest.load()
    if S.PENDING.exists():
        _close_pending(m, "rejected", R.REJECTED_RGB, f"run restarted: {args.reason}")
        S.PENDING_IDX.unlink(missing_ok=True)
        S.PENDING.unlink()
    when = S.now_local()
    slug = "".join(c if c.isalnum() else "_" for c in args.reason.lower())[:40].strip("_")
    dest = S.BUILD / "archive" / f"{when.strftime('%Y%m%d-%H%M%S')}_{slug}"
    dest.mkdir(parents=True)
    m.data["closed"] = {"at": when.isoformat(timespec="seconds"), "reason": args.reason}
    m.save()
    for sub in (S.MANIFEST, S.REMOVED, S.PARTS):
        if sub.exists():
            sub.replace(dest / sub.name)
    for ply in dest.rglob("*.ply"):                       # part .ply files are rebuilt from indices; do not archive
        ply.unlink()
    args.previous = [{"archive": S.rel(dest), "reason": args.reason,
                      "images": [s["image"] for s in m.data["steps"]]}] + m.data.get("previous_runs", [])
    log.info("archived the run to %s (%d steps)", S.rel(dest), len(m.data["steps"]))
    return cmd_init(args)


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
        imgs = s.get("images", [s.get("image")])
        more = f" (+{len(imgs) - 1} more)" if len(imgs) > 1 else ""
        print(f"  {s['index']:04d}  {s['kind']:<8} {s['name']:<24} {s['status']:<9} {imgs[0]}{more}")
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
    p = sub.add_parser("restart", help="archive the current run and start a new empty build")
    p.add_argument("--reason", required=True, help="why (kept in both manifests)")
    p.set_defaults(fn=cmd_restart, force=True)
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
    p = sub.add_parser("probe", help="pictures that help pick a ceiling level (no state change)")
    p.add_argument("--levels", type=float, nargs="+", required=True)
    p.add_argument("--labels", nargs="*", default=[], help="one label per level")
    p.add_argument("--white", type=int, default=240, help="min RGB treated as lamp")
    p.add_argument("--y-lo", type=float, default=0.5)
    p.add_argument("--y-hi", type=float, default=1.65)
    p.set_defaults(fn=cmd_probe)
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
