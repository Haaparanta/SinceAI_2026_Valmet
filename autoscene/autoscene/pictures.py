"""Stage 9: a picture of every object as it joins the room.

Per object, in true colours and textures (Gaussian-splat render):
  a  close-up: the object fully opaque, everything else see-through, its oriented box drawn,
  b  the room from outside: objects built so far in colour, this one highlighted, the rest faint,
  c  the detector's best view: the rendered picture it was found in, with the detection box (proof).
Plus one "every object its own colour" picture of the finished room, a contact sheet, and a flipbook video.
Files: out/images/NNNN_YYYYMMDD-HHMMSS_<object>_<a|b|c>.png (local time), numbering continuing in images/.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson
from PIL import Image, ImageDraw

from autoscene import rasterize as RZ
from autoscene import render as R
from autoscene.scene import Scene
from autoscene.views import VIEW_H, VIEW_W, frustum_cull

log = logging.getLogger("autoscene.pictures")

W, H = R.WIDTH, R.HEIGHT - R.BANNER_H            # 1280 x 736 picture + 64 px banner
HIGHLIGHT = (46, 230, 120)
BOX_RGB = (255, 196, 0)
IMAGE_RE = re.compile(r"^(\d{4,})_")


def next_index(images: Path) -> int:
    used = [int(m.group(1)) for p in images.glob("*.png") if (m := IMAGE_RE.match(p.name))]
    return max(used, default=0) + 1


def _project(points: np.ndarray, cam: R.Camera, width: int, height: int) -> np.ndarray:
    r, u, f = cam.basis()
    rel = points.astype(np.float64) - np.asarray(cam.position)
    z = np.maximum(rel @ f, 1e-3)
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    return np.c_[width / 2 + focal * (rel @ r) / z, height / 2 - focal * (rel @ u) / z, rel @ f]


def draw_obb(img: np.ndarray, corners: np.ndarray, cam: R.Camera, rgb=BOX_RGB, width: int = 2) -> np.ndarray:
    """12 edges of a box (corners in the order of rebuild.obb_yup) drawn on the picture; edges behind the camera
    are skipped."""
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    pts = _project(corners, cam, img.shape[1], img.shape[0])
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in edges:
        if pts[a, 2] > 0.05 and pts[b, 2] > 0.05:
            d.line((pts[a, 0], pts[a, 1], pts[b, 0], pts[b, 1]), fill=rgb, width=width)
    return np.asarray(im)


def closeup_camera(sc: Scene, p: np.ndarray, fill: float = 0.32) -> R.Camera:
    """From the room's middle towards the object, a little above it, never higher than just under the ceiling (so
    the ceiling pipes do not hide it) and never inside the object. Room-sized objects (floor, walls) get a wide
    framing instead of a close-up."""
    lo, hi = np.percentile(p, 1, 0), np.percentile(p, 99, 0)
    centre = 0.5 * (lo + hi)
    size = float(np.linalg.norm(hi - lo))
    fill = float(np.interp(size, [1.0, 4.0], [fill, 0.85]))
    room_c = 0.5 * (sc.bmin + sc.bmax)
    d = centre - room_c
    d[1] = 0.0
    n = np.linalg.norm(d)
    towards = d / n if n > 0.3 else np.array([0.0, 0.0, -1.0])
    view_dir = np.array([towards[0], -0.45, towards[2]])      # look along the direction from the room centre, down
    if centre[1] > room_c[1] + 0.6:                           # things on the ceiling: look up at them
        view_dir[1] = +0.35
    cam = R.framing_camera(lo, hi, view_dir, fill=fill, fov_deg=55.0, width=W, height=H)
    pos = np.array(cam.position)
    y_max = sc.ceiling_y - 0.35
    if pos[1] > y_max and size < 4.0:
        pos[1] = y_max
        cam = R.Camera(tuple(map(float, pos)), cam.target, cam.fov_deg)
    return cam


def _frame(img: np.ndarray, cam: R.Camera) -> R.Frame:
    return R.Frame(img, np.full(img.shape[:2], np.inf, np.float32), cam, {})


def _save(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(path, optimize=True)


def palette(n: int) -> np.ndarray:
    """n distinct, bright colours (golden-angle hues)."""
    hues = (np.arange(n) * 0.61803398875) % 1.0
    out = []
    for i, h in enumerate(hues):
        s, v = 0.65 + 0.3 * ((i % 3) / 2), 0.95
        k = int(h * 6)
        f = h * 6 - k
        p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
        r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][k % 6]
        out.append((int(r * 255), int(g * 255), int(b * 255)))
    return np.array(out, dtype=np.uint8)


def pictures(sc: Scene, out: Path, limit: int = 0, shard: tuple[int, int] = (0, 1), image_base: int = 0) -> None:
    """Pictures a, b, c for every object (or those with index % shard[1] == shard[0], so several processes can share
    the work). Image numbers are fixed per object (image_base + 3 x position + slot), so shards never collide."""
    scene = orjson.loads((out / "scene.json").read_bytes())
    z = np.load(out / "objects.npz")
    objects = scene["objects"]
    offsets = np.r_[0, np.cumsum(z["sizes"])]
    rows_of = [z["splats"][offsets[i]:offsets[i + 1]] for i in range(len(objects))]
    images = out / "images"
    images.mkdir(parents=True, exist_ok=True)
    image_base = image_base or next_index(images)
    kept = sc.kept_idx()
    outside = R.outside_camera(sc.bmin, sc.bmax, width=W, height=H)
    built = np.zeros(sc.n, dtype=bool)
    views_meta = orjson.loads((out / "views" / "views.json").read_bytes())["views"]
    det_table = np.load(out / "detections.npz")["table"] if (out / "detections.npz").exists() else None
    manifest = []
    todo = objects[:limit] if limit else objects
    for k, (obj, rows) in enumerate(zip(todo, rows_of)):
        if k % shard[1] != shard[0]:
            built[rows] = True
            continue
        index = image_base + 3 * k
        when = datetime.now().astimezone()
        stamp = when.strftime("%Y%m%d-%H%M%S")
        name = obj["name"]
        p = sc.xyz[rows]
        corners = np.array(obj["obb"]["corners"])
        title = f"{obj['index']:03d} · ADD {obj['label'].upper()} · {obj['n_splats']:,} splats"
        ext = obj["obb"]["extent"]
        sub = (f"{obj['source']} · confidence {obj['confidence']:.2f} · box {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} u"
               f" · seen in {len(obj['views'])} views · centre ({', '.join(f'{v:+.2f}' for v in obj['obb']['center'])})")
        files = {}
        # a) close-up, textured: object opaque, context see-through
        cam = closeup_camera(sc, p)
        j = kept[frustum_cull(sc.xyz[kept], cam, W, H)]
        alpha_scale = np.full(sc.n, 0.12, np.float32)
        alpha_scale[rows] = 1.0
        color_scale = np.full(sc.n, 0.45, np.float32)
        color_scale[rows] = 1.0
        img, _, _ = RZ.render(sc.splats[j], cam, W, H, ids=j, alpha_scale=alpha_scale, color_scale=color_scale)
        img = draw_obb(img, corners, cam)
        im = R.compose(_frame(img, cam), title, sub, [(HIGHLIGHT, "new object 100 %"), ((120, 124, 136), "rest 12 %, dimmed")],
                       when, badge="ADDED", badge_rgb=R.ACCEPTED_RGB, headline=f"added: {obj['label']}",
                       headline_rgb=HIGHLIGHT)
        files["closeup"] = images / f"{index:04d}_{stamp}_{name}_a.png"
        _save(im, files["closeup"])
        index += 1
        # b) the room from outside: built in colour, this object highlighted, rest faint
        rest = kept[~built[kept] & ~np.isin(kept, rows, assume_unique=False)][::4]      # faint: every 4th is enough
        built_idx = np.flatnonzero(built)[::2]
        layers = [
            R.BlendLayer(sc.xyz[rest], sc.rgb[rest], 0.08, "rest", sc.size[rest] * 1.4),
            R.BlendLayer(sc.xyz[built_idx], sc.rgb[built_idx], 0.26, "built", sc.size[built_idx] * 1.2),
            R.BlendLayer(sc.xyz[rows], R.tint(sc.rgb[rows], HIGHLIGHT, 0.75), 0.95, "new", sc.size[rows], 4),
        ]
        fr = R.render_blend(layers, outside, W, H)
        img = draw_obb(fr.image, corners, outside)
        im = R.compose(_frame(img, outside), title, sub, [(HIGHLIGHT, "new 95 %"), ((150, 150, 150), "built 22 %"),
                                                          ((75, 75, 80), "rest 5 %")], when, badge="ADDED",
                       badge_rgb=R.ACCEPTED_RGB, headline=f"room so far: {k + 1} of {len(todo)} objects",
                       headline_rgb=HIGHLIGHT)
        files["outside"] = images / f"{index:04d}_{stamp}_{name}_b.png"
        _save(im, files["outside"])
        index += 1
        # c) proof: the detector's best view with its box
        if obj["source"] == "yoloe" and det_table is not None and obj["detections"]:
            best = max(obj["detections"], key=lambda d: det_table[d, 2])
            row = det_table[best]
            v = views_meta[int(row[0])]
            vimg = np.asarray(Image.open(out / "views" / f"{v['name']}.png").convert("RGB")).copy()
            x0, y0, x1, y1 = (int(t) for t in row[3:7])
            R.draw_box(vimg, (x0, y0, x1, y1), HIGHLIGHT, pad=6, thick=3)
            sc_ = min(W / VIEW_W, H / VIEW_H)
            vim = Image.fromarray(vimg).resize((int(VIEW_W * sc_), int(VIEW_H * sc_)), Image.LANCZOS)
            canvas = np.zeros((H, W, 3), np.uint8)
            canvas[:] = R.BACKGROUND
            x_off = (W - vim.width) // 2
            canvas[: vim.height, x_off:x_off + vim.width] = np.asarray(vim)
            cam_v = R.Camera(tuple(v["camera"]["position"]), tuple(v["camera"]["target"]), v["camera"]["fov_deg"])
            im = R.compose(_frame(canvas, cam_v), title, f"proof: view {v['name']} · YOLOE {row[2]:.2f} · "
                           f"{len(obj['detections'])} detections across {len(obj['views'])} views", [(HIGHLIGHT, "detection")],
                           when, badge="PROOF", badge_rgb=R.PROPOSED_RGB, headline=f"found as: {obj['label']}",
                           headline_rgb=HIGHLIGHT)
            files["proof"] = images / f"{index:04d}_{stamp}_{name}_c.png"
            _save(im, files["proof"])
            index += 1
        built[rows] = True
        manifest.append({"index": obj["index"], "name": name, "label": obj["label"],
                         "images": {kk: str(vv.relative_to(out)) for kk, vv in files.items()}})
        if k % 10 == 0 or k == len(todo) - 1:
            log.info("pictures %d/%d (%s)", k + 1, len(todo), name)
    (out / f"images_manifest_{shard[0]}.json").write_bytes(orjson.dumps(manifest, option=orjson.OPT_INDENT_2))


def finish(sc: Scene, out: Path) -> None:
    """After every shard: the two finished-room pictures, the merged manifest, the contact sheet and the flipbook."""
    scene = orjson.loads((out / "scene.json").read_bytes())
    z = np.load(out / "objects.npz")
    objects = scene["objects"]
    offsets = np.r_[0, np.cumsum(z["sizes"])]
    rows_of = [z["splats"][offsets[i]:offsets[i + 1]] for i in range(len(objects))]
    images = out / "images"
    kept = sc.kept_idx()
    outside = R.outside_camera(sc.bmin, sc.bmax, width=W, height=H)
    manifest = []
    for p in sorted(out.glob("images_manifest_*.json")):
        manifest += orjson.loads(p.read_bytes())
    manifest.sort(key=lambda m: m["index"])
    index = next_index(images)
    cols = palette(len(objects))
    layers = [R.Layer(sc.xyz[rows], (60, 62, 70) if obj["source"] == "structure" else tuple(int(c) for c in cols[i]),
                      f"o{i}", sc.size[rows], 1 if obj["source"] == "structure" else 3)
              for i, (obj, rows) in enumerate(zip(objects, rows_of))]
    fr = R.render(layers, outside, W, H)
    img = fr.image
    for obj in objects:
        if obj["source"] != "structure":
            img = draw_obb(img, np.array(obj["obb"]["corners"]), outside, rgb=(255, 255, 255), width=1)
    when = datetime.now().astimezone()
    im = R.compose(_frame(img, outside), f"FINISHED ROOM · {len(objects)} objects, each its own colour",
                   ", ".join(f"{k} x{v}" for k, v in sorted(scene["by_label"].items(), key=lambda kv: -kv[1])[:12]),
                   [], when, badge="DONE", badge_rgb=R.ACCEPTED_RGB)
    _save(im, images / f"{index:04d}_{when.strftime('%Y%m%d-%H%M%S')}_all_objects_coloured.png")
    index += 1
    inside = R.overview_camera(sc.bmin, sc.bmax)
    j = kept[frustum_cull(sc.xyz[kept], inside, W, H)]
    img, _, _ = RZ.render(sc.splats[j], inside, W, H, ids=j)
    for obj in objects:
        if obj["source"] != "structure":
            img = draw_obb(img, np.array(obj["obb"]["corners"]), inside, rgb=BOX_RGB, width=1)
    im = R.compose(_frame(img, inside), f"FINISHED ROOM · textured, {len(objects)} framed objects", "", [], when,
                   badge="DONE", badge_rgb=R.ACCEPTED_RGB)
    _save(im, images / f"{index:04d}_{when.strftime('%Y%m%d-%H%M%S')}_all_objects_textured.png")
    (out / "images_manifest.json").write_bytes(orjson.dumps(manifest, option=orjson.OPT_INDENT_2))
    contact_sheet([out / m["images"]["closeup"] for m in manifest], out / "contact_sheet.png")
    flipbook([out / m["images"]["outside"] for m in manifest], out / "flipbook.mp4")


def contact_sheet(paths: list[Path], out: Path, cols: int = 6, thumb: tuple[int, int] = (320, 200)) -> None:
    if not paths:
        return
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb[0], rows * thumb[1]), (6, 7, 12))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize(thumb, Image.LANCZOS)
        sheet.paste(im, ((i % cols) * thumb[0], (i // cols) * thumb[1]))
    sheet.save(out, optimize=True)


def flipbook(paths: list[Path], out: Path, fps: int = 4) -> None:
    """MP4 of the outside views (imageio + bundled ffmpeg); falls back to a GIF if imageio is missing."""
    if not paths:
        return
    try:
        import imageio.v2 as iio
        with iio.get_writer(out, fps=fps, codec="libx264", quality=7, macro_block_size=8) as w:
            for p in paths:
                w.append_data(np.asarray(Image.open(p).convert("RGB")))
    except ImportError:
        frames = [Image.open(p).convert("RGB").resize((640, 400)) for p in paths]
        frames[0].save(out.with_suffix(".gif"), save_all=True, append_images=frames[1:], duration=int(1000 / fps),
                       loop=0)
