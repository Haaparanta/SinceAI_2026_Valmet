"""Stage 4: pictures of the room for the 2D detector, each with an ID buffer (which splat made each pixel).

Cameras stand on a grid inside the room at eye height and turn in 8 directions with two pitches, plus plan views
from above. The render is the CPU point renderer with eye-dome lighting (about 1.5 s per view); the splat renderer
is 10-50 x slower and is kept for the per-object pictures.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from autoscene import render as R
from autoscene.scene import Scene

log = logging.getLogger("autoscene.views")

VIEW_W, VIEW_H = 1024, 640


@dataclass
class View:
    name: str
    camera: R.Camera
    image: np.ndarray | None = None       # uint8[H, W, 3]
    ids: np.ndarray | None = None         # int32[H, W], -1 where empty: index into the scene's splats
    depth: np.ndarray | None = None


def render_ids(xyz: np.ndarray, rgb: np.ndarray, size: np.ndarray, ids: np.ndarray, cam: R.Camera,
               width: int = VIEW_W, height: int = VIEW_H, max_radius_px: int = 3, edl: float = 1.0,
               near: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """render.render with an ID buffer: (image, ids, depth). Nearest footprint wins per pixel."""
    r, u, f = cam.basis()
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    rel = xyz.astype(np.float64) - np.asarray(cam.position)
    z = rel @ f
    front = z > near
    rel, z, col, ws, gid = rel[front], z[front], rgb[front], size[front], ids[front]
    px = width / 2 + focal * (rel @ r) / z
    py = height / 2 - focal * (rel @ u) / z
    inside = (px > -4) & (px < width + 4) & (py > -4) & (py < height + 4)
    px, py, z, col, ws, gid = px[inside], py[inside], z[inside], col[inside], ws[inside], gid[inside]
    rad = np.clip(np.rint(0.5 * focal * ws / z), 0, max_radius_px).astype(int)
    pix_l, dep_l, col_l, id_l = [], [], [], []
    for rr in np.unique(rad):
        sel = rad == rr
        for dx, dy in R._disc_offsets(int(rr)):
            xi = np.rint(px[sel]).astype(np.int64) + dx
            yi = np.rint(py[sel]).astype(np.int64) + dy
            ok = (xi >= 0) & (xi < width) & (yi >= 0) & (yi < height)
            pix_l.append(yi[ok] * width + xi[ok])
            dep_l.append(z[sel][ok].astype(np.float32))
            col_l.append(col[sel][ok])
            id_l.append(gid[sel][ok])
    img = np.empty((height * width, 3), dtype=np.uint8)
    img[:] = R.BACKGROUND
    depth = np.full(height * width, np.inf, dtype=np.float32)
    out_ids = np.full(height * width, -1, dtype=np.int32)
    if pix_l:
        pix, dep = np.concatenate(pix_l), np.concatenate(dep_l)
        col, gi = np.concatenate(col_l), np.concatenate(id_l)
        order = np.lexsort((dep, pix))
        pix, dep, col, gi = pix[order], dep[order], col[order], gi[order]
        first = np.ones(len(pix), dtype=bool)
        first[1:] = pix[1:] != pix[:-1]
        img[pix[first]] = col[first]
        depth[pix[first]] = dep[first]
        out_ids[pix[first]] = gi[first]
    img = img.reshape(height, width, 3)
    depth = depth.reshape(height, width)
    if edl > 0:
        img = R._eye_dome(img, depth, edl)
    return img, out_ids.reshape(height, width), depth


# ---------------------------------------------------------------- camera set


def camera_set(sc: Scene, eye_above_floor: float = 1.45, cols: int = 4, rows: int = 3, yaws: int = 8,
               pitches: tuple[float, ...] = (-15.0, 10.0), fov_deg: float = 70.0, inset: float = 0.15) -> list[View]:
    """Eye-height cameras on a cols x rows grid inside the room (inset from the walls), each turning through
    `yaws` headings at each pitch (degrees, negative = looking down), plus four plan views from above the ceiling
    looking down at the quarters of the room and one whole-room plan."""
    lo, hi = sc.bmin.copy(), sc.bmax.copy()
    floor_y = float(np.median(sc.floor_y_at(np.array([[0.5 * (lo[0] + hi[0]), 0.0, 0.5 * (lo[2] + hi[2])]]))))
    eye_y = floor_y + eye_above_floor
    xs = lo[0] + (hi[0] - lo[0]) * (inset + (1 - 2 * inset) * np.arange(cols) / max(cols - 1, 1))
    zs = lo[2] + (hi[2] - lo[2]) * (inset + (1 - 2 * inset) * np.arange(rows) / max(rows - 1, 1))
    views: list[View] = []
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            for k in range(yaws):
                yaw = 2 * np.pi * k / yaws
                for pitch in pitches:
                    p = np.radians(pitch)
                    d = np.array([np.sin(yaw) * np.cos(p), np.sin(p), np.cos(yaw) * np.cos(p)])
                    pos = np.array([x, eye_y, z])
                    cam = R.Camera(tuple(map(float, pos)), tuple(map(float, pos + d)), fov_deg)
                    views.append(View(f"g{i}{j}_y{int(np.degrees(yaw)):03d}_p{int(pitch):+03d}", cam))
    # plan views: whole room and four quarters
    views.append(View("plan_all", R.plan_camera(lo, hi, fill=0.9, width=VIEW_W, height=VIEW_H)))
    mid = 0.5 * (lo + hi)
    for name, (x0, x1) in (("w", (lo[0], mid[0])), ("e", (mid[0], hi[0]))):
        for name2, (z0, z1) in (("n", (lo[2], mid[2])), ("s", (mid[2], hi[2]))):
            qlo, qhi = np.array([x0, lo[1], z0]), np.array([x1, hi[1], z1])
            views.append(View(f"plan_{name}{name2}", R.plan_camera(qlo, qhi, fill=0.9, width=VIEW_W, height=VIEW_H)))
    return views


def render_views(sc: Scene, views: list[View], out: Path, idx: np.ndarray | None = None,
                 hide_ceiling_for_plan: bool = True, width: int = VIEW_W, height: int = VIEW_H) -> list[View]:
    """Render every view with the Gaussian-splat rasteriser (rasterize.render, frustum-culled) to out/<name>.png,
    <name>.ids.npz (splat index per pixel, -1 = background) and a views.json with the cameras. `idx` restricts the
    splats drawn (default: every kept splat). Plan views hide the ceiling so the room is visible from above."""
    from autoscene import rasterize as RZ
    out.mkdir(parents=True, exist_ok=True)
    idx = sc.kept_idx() if idx is None else idx
    no_ceiling = idx[sc.structure[idx] != 2]
    meta = []
    t0 = time.time()
    for i, v in enumerate(views):
        base = no_ceiling if (v.name.startswith("plan") and hide_ceiling_for_plan) else idx
        j = base[frustum_cull(sc.xyz[base], v.camera, width, height)]
        img, ids, depth = RZ.render(sc.splats[j], v.camera, width, height, ids=j)
        v.image, v.ids, v.depth = img, ids, depth
        Image.fromarray(img).save(out / f"{v.name}.png")
        np.savez_compressed(out / f"{v.name}.ids.npz", ids=ids, depth=depth.astype(np.float16))
        meta.append({"name": v.name, "camera": v.camera.to_dict(), "up": list(v.camera.up),
                     "filled": int((ids >= 0).mean() * 1000) / 10, "splats": len(j)})
        if i % 10 == 0 or i == len(views) - 1:
            log.info("rendered %d/%d views (%.0f s)", i + 1, len(views), time.time() - t0)
    (out / "views.json").write_text(json.dumps({"width": width, "height": height, "views": meta}, indent=1))
    return views


def load_view_data(v: View, out: Path) -> View:
    v.image = np.asarray(Image.open(out / f"{v.name}.png").convert("RGB"))
    z = np.load(out / f"{v.name}.ids.npz")
    v.ids, v.depth = z["ids"], z["depth"].astype(np.float32)
    return v


def load_views(out: Path) -> list[View]:
    """The cameras of a rendered set (pictures and ID buffers are loaded per view with load_view_data)."""
    meta = json.loads((out / "views.json").read_text())
    views = []
    for m in meta["views"]:
        c = m["camera"]
        cam = R.Camera(tuple(c["position"]), tuple(c["target"]), c["fov_deg"], tuple(m.get("up", (0, 1, 0))))
        v = View(m["name"], cam)
        views.append(v)
    return views


# ---------------------------------------------------------------- Gaussian splat render with an ID buffer


def frustum_cull(xyz: np.ndarray, cam: R.Camera, width: int, height: int, margin: float = 0.15,
                 near: float = 0.05) -> np.ndarray:
    """Bool: splat centres that project inside the picture (with a relative `margin` outside it)."""
    r, u, f = cam.basis()
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    rel = xyz.astype(np.float64) - np.asarray(cam.position)
    z = rel @ f
    ok = z > near
    zz = np.where(ok, z, 1.0)
    px = width / 2 + focal * (rel @ r) / zz
    py = height / 2 - focal * (rel @ u) / zz
    mw, mh = margin * width, margin * height
    return ok & (px > -mw) & (px < width + mw) & (py > -mh) & (py < height + mh)


def render_splats_ids(splats: np.ndarray, ids: np.ndarray, cam: R.Camera, width: int, height: int,
                      max_radius_px: int = 8, near: float = 0.1, background=R.BACKGROUND, chunk: int = 150_000
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """render.render_gaussians plus an ID buffer: per pixel the splat with the largest share of the pixel colour
    (and its depth). Returns (image uint8[H,W,3], ids int32[H,W] (-1 = background), depth float32[H,W])."""
    r, u, f = cam.basis()
    W = np.stack([r, u, f])
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    n_pix = width * height
    pix_l, dep_l, col_l, a_l, id_l = [], [], [], [], []
    for c0 in range(0, len(splats), chunk):
        s, gid = splats[c0:c0 + chunk], ids[c0:c0 + chunk]
        p = np.stack([s["x"], s["y"], s["z"]], 1).astype(np.float64) - np.asarray(cam.position)
        t = p @ W.T
        keep = t[:, 2] > near
        s, t, gid = s[keep], t[keep], gid[keep]
        if len(s) == 0:
            continue
        sc = np.exp(np.clip(np.stack([s["scale_0"], s["scale_1"], s["scale_2"]], 1), -30, 2)).astype(np.float64)
        q = np.stack([s["rot_0"], s["rot_1"], s["rot_2"], s["rot_3"]], 1).astype(np.float64)
        q /= np.linalg.norm(q, axis=1, keepdims=True)
        qw, qx, qy, qz = q.T
        Rm = np.stack([
            np.stack([1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qw * qz), 2 * (qx * qz + qw * qy)], 1),
            np.stack([2 * (qx * qy + qw * qz), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qw * qx)], 1),
            np.stack([2 * (qx * qz - qw * qy), 2 * (qy * qz + qw * qx), 1 - 2 * (qx * qx + qy * qy)], 1),
        ], 1)
        M = (W[None] @ Rm) * sc[:, None, :]
        cov = M @ np.transpose(M, (0, 2, 1))
        x, y, z = t.T
        J = np.zeros((len(s), 2, 3))
        J[:, 0, 0] = focal / z
        J[:, 0, 2] = -focal * x / (z * z)
        J[:, 1, 1] = -focal / z
        J[:, 1, 2] = focal * y / (z * z)
        c2 = J @ cov @ np.transpose(J, (0, 2, 1))
        a_, b_, d_ = c2[:, 0, 0] + 0.3, c2[:, 0, 1], c2[:, 1, 1] + 0.3
        det = a_ * d_ - b_ * b_
        ok = det > 1e-12
        mid = 0.5 * (a_ + d_)
        lam = mid + np.sqrt(np.maximum(mid * mid - det, 0))
        rad = np.minimum(np.ceil(3 * np.sqrt(lam)), max_radius_px).astype(int)
        px = width / 2 + focal * x / z
        py = height / 2 - focal * y / z
        ok &= (px + rad >= 0) & (px - rad < width) & (py + rad >= 0) & (py - rad < height)
        ia, ib, id_ = d_ / det, -b_ / det, a_ / det
        opa = 1.0 / (1.0 + np.exp(-np.clip(s["opacity"].astype(np.float64), -30, 30)))
        dc = np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], 1).astype(np.float64)
        rgb = np.clip(0.5 + 0.28209479 * dc, 0, 1) * 255.0
        for rr in np.unique(rad[ok]):
            sel = np.flatnonzero(ok & (rad == rr))
            cx, cy = np.rint(px[sel]).astype(np.int64), np.rint(py[sel]).astype(np.int64)
            fx, fy = px[sel] - cx, py[sel] - cy
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    ex, ey = dx - fx, dy - fy
                    power = -0.5 * (ia[sel] * ex * ex + 2 * ib[sel] * ex * ey + id_[sel] * ey * ey)
                    alpha = opa[sel] * np.exp(np.maximum(power, -30))
                    xi, yi = cx + dx, cy + dy
                    m = (alpha >= 1 / 255) & (xi >= 0) & (xi < width) & (yi >= 0) & (yi < height)
                    if not m.any():
                        continue
                    pix_l.append(yi[m] * width + xi[m])
                    dep_l.append(z[sel][m].astype(np.float32))
                    col_l.append(rgb[sel][m].astype(np.float32))
                    a_l.append(np.minimum(alpha[m], 0.99).astype(np.float32))
                    id_l.append(gid[sel][m])
    img = np.broadcast_to(np.asarray(background, np.uint8), (height, width, 3)).copy()
    out_ids = np.full(n_pix, -1, dtype=np.int32)
    depth = np.full(n_pix, np.inf, dtype=np.float32)
    if not pix_l:
        return img, out_ids.reshape(height, width), depth.reshape(height, width)
    pix, dep = np.concatenate(pix_l), np.concatenate(dep_l)
    col, a, gi = np.concatenate(col_l), np.concatenate(a_l), np.concatenate(id_l)
    order = np.lexsort((dep, pix))
    pix, dep, col, a, gi = pix[order], dep[order], col[order], a[order], gi[order]
    first = np.ones(len(pix), dtype=bool)
    first[1:] = pix[1:] != pix[:-1]
    la = np.log1p(-np.minimum(a, 0.999).astype(np.float64))
    cs = np.cumsum(la)
    start = np.flatnonzero(first)
    group = np.cumsum(first) - 1
    base = (cs[start] - la[start])[group]
    w = a * np.exp(cs - la - base)
    out = np.stack([np.bincount(pix, weights=w * col[:, k], minlength=n_pix) for k in range(3)], 1)
    trans = np.exp(np.bincount(pix, weights=la, minlength=n_pix))
    out += trans[:, None] * np.asarray(background, np.float64)
    # ID = the fragment with the largest share of its pixel
    best = np.lexsort((-w, pix))
    bpix, bw, bgi, bdep = pix[best], w[best], gi[best], dep[best]
    bfirst = np.ones(len(bpix), dtype=bool)
    bfirst[1:] = bpix[1:] != bpix[:-1]
    solid = bfirst & (bw >= 0.05)           # a background pixel barely touched by fog keeps no id
    out_ids[bpix[solid]] = bgi[solid]
    depth[bpix[solid]] = bdep[solid]
    img = np.clip(np.rint(out), 0, 255).astype(np.uint8).reshape(height, width, 3)
    return img, out_ids.reshape(height, width), depth.reshape(height, width)
