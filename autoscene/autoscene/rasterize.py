"""Fast CPU Gaussian-splat rasteriser (numba) with an ID buffer.

Same maths as render.render_gaussians (EWA projection of each splat's 3D covariance to a 2D ellipse, alpha =
opacity * exp(-d^T S^-1 d / 2), front-to-back compositing), but the per-pixel blending runs in a compiled loop over the
splats sorted by depth, with early termination once a pixel is opaque. 10-100 x faster than the numpy version, which
made 100 detector views cost hours on the M1.
"""

from __future__ import annotations

import numpy as np
from numba import njit

from autoscene import render as R


def project(splats: np.ndarray, cam: R.Camera, width: int, height: int, near: float = 0.1,
            max_radius_px: int = 12, chunk: int = 200_000) -> dict:
    """Vectorised projection in chunks (peak memory ~150 MB instead of ~1 GB for the whole room): per splat the
    screen centre, inverse 2D covariance, radius, depth, colour, opacity, sorted front to back. Splats behind the
    camera or outside the picture are dropped."""
    parts = [_project_chunk(splats[c0:c0 + chunk], c0, cam, width, height, near, max_radius_px)
             for c0 in range(0, len(splats), chunk)]
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]} if parts else _project_chunk(
        splats, 0, cam, width, height, near, max_radius_px)
    order = np.argsort(out["z"], kind="stable")
    return {k: v[order] for k, v in out.items()}


def _project_chunk(splats: np.ndarray, offset: int, cam: R.Camera, width: int, height: int, near: float,
                   max_radius_px: int) -> dict:
    r, u, f = cam.basis()
    W = np.stack([r, u, f])
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    p = np.stack([splats["x"], splats["y"], splats["z"]], 1).astype(np.float64) - np.asarray(cam.position)
    t = p @ W.T
    keep = t[:, 2] > near
    s, t, src = splats[keep], t[keep], np.flatnonzero(keep) + offset
    sc = np.exp(np.clip(np.stack([s["scale_0"], s["scale_1"], s["scale_2"]], 1), -30, 2)).astype(np.float64)
    q = np.stack([s["rot_0"], s["rot_1"], s["rot_2"], s["rot_3"]], 1).astype(np.float64)
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-9)
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
    rad = np.minimum(np.ceil(3 * np.sqrt(lam)), max_radius_px).astype(np.int32)
    px = width / 2 + focal * x / z
    py = height / 2 - focal * y / z
    ok &= (px + rad >= 0) & (px - rad < width) & (py + rad >= 0) & (py - rad < height)
    det = np.where(ok, det, 1.0)
    opa = 1.0 / (1.0 + np.exp(-np.clip(s["opacity"].astype(np.float64), -30, 30)))
    dc = np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], 1).astype(np.float64)
    rgb = np.clip(0.5 + 0.28209479 * dc, 0, 1)
    ok &= opa >= 1 / 255
    order = np.flatnonzero(ok)
    return {
        "px": px[order].astype(np.float32), "py": py[order].astype(np.float32),
        "ia": (d_ / det)[order].astype(np.float32), "ib": (-b_ / det)[order].astype(np.float32),
        "id": (a_ / det)[order].astype(np.float32), "rad": rad[order], "z": z[order].astype(np.float32),
        "opa": opa[order].astype(np.float32), "rgb": rgb[order].astype(np.float32), "src": src[order],
    }


@njit(cache=True, fastmath=True)
def _raster(px, py, ia, ib, idd, rad, z, opa, rgb, src, width, height, bg, img, ids, depth, weight, trans):
    n = len(px)
    for i in range(n):
        cx, cy = px[i], py[i]
        r = rad[i]
        x0 = max(int(np.floor(cx)) - r, 0)
        x1 = min(int(np.ceil(cx)) + r, width - 1)
        y0 = max(int(np.floor(cy)) - r, 0)
        y1 = min(int(np.ceil(cy)) + r, height - 1)
        if x1 < x0 or y1 < y0:
            continue
        a, b, d = ia[i], ib[i], idd[i]
        o = opa[i]
        cr, cg, cb = rgb[i, 0], rgb[i, 1], rgb[i, 2]
        for yy in range(y0, y1 + 1):
            ey = yy - cy
            for xx in range(x0, x1 + 1):
                T = trans[yy, xx]
                if T < 0.003:
                    continue
                ex = xx - cx
                power = -0.5 * (a * ex * ex + 2.0 * b * ex * ey + d * ey * ey)
                if power < -4.5:          # 3 sigma
                    continue
                alpha = o * np.exp(power)
                if alpha < 1.0 / 255.0:
                    continue
                alpha = min(alpha, 0.99)
                w = alpha * T
                img[yy, xx, 0] += w * cr
                img[yy, xx, 1] += w * cg
                img[yy, xx, 2] += w * cb
                if w > weight[yy, xx]:
                    weight[yy, xx] = w
                    ids[yy, xx] = src[i]
                    depth[yy, xx] = z[i]
                trans[yy, xx] = T * (1.0 - alpha)
    for yy in range(height):
        for xx in range(width):
            T = trans[yy, xx]
            img[yy, xx, 0] += T * bg[0]
            img[yy, xx, 1] += T * bg[1]
            img[yy, xx, 2] += T * bg[2]


def render(splats: np.ndarray, cam: R.Camera, width: int, height: int, ids: np.ndarray | None = None,
           max_radius_px: int = 12, near: float = 0.1, background=R.BACKGROUND, min_weight: float = 0.05,
           alpha_scale: np.ndarray | None = None, color_scale: np.ndarray | None = None
           ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(image uint8[H,W,3], ids int32[H,W] (-1 = background; index into `ids`, default the row of `splats`),
    depth float32[H,W]). `alpha_scale` (float per splat) multiplies the opacity and `color_scale` the brightness:
    used to draw the context faint and dim behind a highlighted object."""
    P = project(splats, cam, width, height, near, max_radius_px)
    src = P["src"] if ids is None else ids[P["src"]]
    opa = P["opa"] if alpha_scale is None else (P["opa"] * alpha_scale[src]).astype(np.float32)
    if color_scale is not None:
        P["rgb"] = (P["rgb"] * color_scale[src][:, None]).astype(np.float32)
    img = np.zeros((height, width, 3), dtype=np.float32)
    out_ids = np.full((height, width), -1, dtype=np.int32)
    depth = np.full((height, width), np.inf, dtype=np.float32)
    weight = np.zeros((height, width), dtype=np.float32)
    trans = np.ones((height, width), dtype=np.float32)
    bg = np.asarray(background, dtype=np.float32) / 255.0
    _raster(P["px"], P["py"], P["ia"], P["ib"], P["id"], P["rad"], P["z"], opa, P["rgb"], src.astype(np.int32),
            width, height, bg, img, out_ids, depth, weight, trans)
    faint = weight < min_weight
    out_ids[faint] = -1
    depth[faint] = np.inf
    return np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8), out_ids, depth
