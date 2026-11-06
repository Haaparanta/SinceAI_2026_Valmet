"""CPU point renderer for the step images: numpy z-buffer + eye-dome lighting, Pillow for text. No GPU needed.

Points are drawn as small round footprints whose pixel radius follows their depth, the nearest point wins per pixel,
and eye-dome lighting (EDL) darkens depth edges so flat grey and red parts still show their shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 800
BACKGROUND = (11, 13, 20)
RED = (255, 45, 85)       # the new / candidate part (AGENTS.md S3 snapshot recipe 0xff2d55)
GREY = (154, 160, 166)    # accepted parts (0x9aa0a6)
FAINT = (70, 74, 82)      # optional context points
BANNER_H = 64


@dataclass(frozen=True)
class Camera:
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov_deg: float = 50.0                       # vertical
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        f = np.subtract(self.target, self.position).astype(np.float64)
        f /= np.linalg.norm(f)
        r = np.cross(f, self.up)
        r /= np.linalg.norm(r)
        return r, np.cross(r, f), f

    def to_dict(self) -> dict:
        return {"position": [round(v, 4) for v in self.position], "target": [round(v, 4) for v in self.target],
                "fov_deg": self.fov_deg}


@dataclass
class Layer:
    """Points of one colour role. `rgb` is one colour for all points or uint8[n, 3] per point."""
    xyz: np.ndarray
    rgb: tuple[int, int, int] | np.ndarray
    name: str = ""
    world_size: float | np.ndarray = 0.012      # footprint diameter in scene units (scalar or per point)
    max_radius_px: int = 3


@dataclass
class Frame:
    image: np.ndarray                           # uint8[H, W, 3]
    depth: np.ndarray                           # float32[H, W], inf where empty
    camera: Camera
    counts: dict[str, int] = field(default_factory=dict)  # visible pixels per layer name


def _disc_offsets(r: int) -> np.ndarray:
    d = np.arange(-r, r + 1)
    dx, dy = np.meshgrid(d, d)
    keep = dx**2 + dy**2 <= r * r + r       # a slightly full disc
    return np.stack([dx[keep], dy[keep]], 1)


def render(layers: list[Layer], cam: Camera, width: int = WIDTH, height: int = HEIGHT,
           edl_strength: float = 1.0) -> Frame:
    r, u, f = cam.basis()
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    pix_all, depth_all, col_all, layer_all = [], [], [], []
    for li, layer in enumerate(layers):
        if len(layer.xyz) == 0:
            continue
        rel = layer.xyz.astype(np.float64) - np.asarray(cam.position)
        z = rel @ f
        front = z > 0.05
        rel, z = rel[front], z[front]
        px = width / 2 + focal * (rel @ r) / z
        py = height / 2 - focal * (rel @ u) / z
        if isinstance(layer.rgb, np.ndarray):
            col = layer.rgb[front]
        else:
            col = np.broadcast_to(np.asarray(layer.rgb, dtype=np.uint8), (len(z), 3))
        ws = layer.world_size[front] if isinstance(layer.world_size, np.ndarray) else layer.world_size
        rad = np.clip(np.rint(0.5 * focal * ws / z), 0, layer.max_radius_px).astype(int)
        for rr in np.unique(rad):
            sel = rad == rr
            for dx, dy in _disc_offsets(int(rr)):
                xi = np.rint(px[sel]).astype(np.int64) + dx
                yi = np.rint(py[sel]).astype(np.int64) + dy
                ok = (xi >= 0) & (xi < width) & (yi >= 0) & (yi < height)
                pix_all.append(yi[ok] * width + xi[ok])
                depth_all.append(z[sel][ok].astype(np.float32))
                col_all.append(col[sel][ok])
                layer_all.append(np.full(int(ok.sum()), li, dtype=np.int16))
    img = np.empty((height * width, 3), dtype=np.uint8)
    img[:] = BACKGROUND
    depth = np.full(height * width, np.inf, dtype=np.float32)
    counts = {layer.name: 0 for layer in layers}
    if pix_all:
        pix = np.concatenate(pix_all)
        dep = np.concatenate(depth_all)
        col = np.concatenate(col_all)
        lay = np.concatenate(layer_all)
        order = np.lexsort((dep, pix))                      # by pixel, nearest first
        pix, dep, col, lay = pix[order], dep[order], col[order], lay[order]
        first = np.ones(len(pix), dtype=bool)
        first[1:] = pix[1:] != pix[:-1]
        img[pix[first]] = col[first]
        depth[pix[first]] = dep[first]
        vis = np.bincount(lay[first], minlength=len(layers))
        counts = {layer.name: int(vis[i]) for i, layer in enumerate(layers)}
    img = img.reshape(height, width, 3)
    depth = depth.reshape(height, width)
    if edl_strength > 0:
        img = _eye_dome(img, depth, edl_strength)
    return Frame(img, depth, cam, counts)


def _eye_dome(img: np.ndarray, depth: np.ndarray, strength: float, radius: int = 2) -> np.ndarray:
    """Classic EDL: shade by how much nearer the neighbours are, in log depth. Empty neighbours add nothing, so
    isolated points stay solid dots instead of turning into rings."""
    filled = np.isfinite(depth)
    if not filled.any():
        return img
    logd = np.where(filled, np.log(np.where(filled, depth, 1.0)), 0.0)
    resp = np.zeros_like(logd)
    for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius),
                   (radius, radius), (-radius, -radius), (radius, -radius), (-radius, radius)):
        nb = np.roll(np.roll(logd, dy, 0), dx, 1)
        nb_filled = np.roll(np.roll(filled, dy, 0), dx, 1)
        resp += np.where(nb_filled, np.maximum(0.0, logd - nb), 0.0)
    shade = np.exp(-strength * 40.0 * resp / 8.0)
    out = img.astype(np.float32)
    out[filled] *= shade[filled, None]
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- cameras


def overview_camera(bmin: np.ndarray, bmax: np.ndarray, fov_deg: float = 50.0) -> Camera:
    """Room overview from the open (camera) side, +z, just under the ceiling, looking at the middle of the back half.

    The scan has no front wall and was captured from +z, so this is the side the room can be seen from without
    looking through a wall or the ceiling."""
    c = 0.5 * (bmin + bmax)
    size = bmax - bmin
    target = np.array([c[0], bmin[1] + 0.35 * size[1], bmin[2] + 0.4 * size[2]])
    half_w = 0.5 * size[0] * 1.08
    aspect = WIDTH / (HEIGHT - BANNER_H)
    dist = half_w / (np.tan(np.radians(fov_deg) / 2) * aspect)
    pos = np.array([c[0], bmax[1] - 0.08 * size[1], bmax[2] + dist * 0.55])
    return Camera(tuple(map(float, pos)), tuple(map(float, target)), fov_deg)


def box_corners(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return np.array([[(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]] for i in (0, 1) for j in (0, 1) for k in (0, 1)])


def screen_span(points: np.ndarray, cam: Camera, width: int = WIDTH, height: int = HEIGHT - BANNER_H
                ) -> tuple[float, float]:
    """(width share, height share) of the frame covered by the projected points' 2D bounding box."""
    r, u, f = cam.basis()
    rel = points - np.asarray(cam.position)
    z = np.maximum(rel @ f, 1e-6)
    focal = 0.5 * height / np.tan(np.radians(cam.fov_deg) / 2)
    px, py = focal * (rel @ r) / z, focal * (rel @ u) / z
    return float(np.ptp(px)) / width, float(np.ptp(py)) / height


def front_elevation_camera(bmin: np.ndarray, bmax: np.ndarray, eye_y: float, look_y: float | None = None,
                           fov_deg: float = 55.0) -> Camera:
    """Camera on the open +z side with its eye at height `eye_y`, looking at the room (-z), wide enough for the whole
    room width. A plane through the eye always projects to a straight line, so with eye_y = floor height the floor
    is a line whatever the tilt: above it is the room, below it is under the floor. `look_y` tilts the view (default:
    the middle of the room height, so floor-to-ceiling fits)."""
    c = 0.5 * (bmin + bmax)
    half_w = 0.5 * (bmax[0] - bmin[0]) * 1.06
    aspect = WIDTH / (HEIGHT - BANNER_H)
    dist = half_w / (np.tan(np.radians(fov_deg) / 2) * aspect)
    ty = float(c[1] if look_y is None else look_y)
    pos = (float(c[0]), float(eye_y), float(c[2] + dist))
    return Camera(pos, (float(c[0]), ty, float(c[2])), fov_deg)


def framing_camera(obj_min: np.ndarray, obj_max: np.ndarray, view_dir: np.ndarray,
                   fill: float = 0.25, fov_deg: float = 50.0) -> Camera:
    """Camera looking along `view_dir` at a box; distance tuned so the box's larger screen share (width or height)
    is `fill` of the frame, leaving the rest for context."""
    center = 0.5 * (obj_min + obj_max)
    corners = box_corners(obj_min, obj_max)
    d = np.asarray(view_dir, dtype=np.float64)
    d /= np.linalg.norm(d)
    radius = max(0.5 * float(np.linalg.norm(obj_max - obj_min)), 1e-3)
    dist = radius / (fill * np.tan(np.radians(fov_deg) / 2))
    for _ in range(6):                                       # span ~ 1/dist; converge in a few steps
        cam = Camera(tuple(map(float, center - d * dist)), tuple(map(float, center)), fov_deg)
        span = max(screen_span(corners, cam))
        dist *= span / fill
        dist = max(dist, radius * 1.05)                      # never put the camera inside the box
    return Camera(tuple(map(float, center - d * dist)), tuple(map(float, center)), fov_deg)


# ---------------------------------------------------------------- banner and file


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def compose(frame: Frame, title: str, subtitle: str, legend: list[tuple[tuple[int, int, int], str]],
            when: datetime, badge: str = "", badge_rgb: tuple[int, int, int] = GREY) -> Image.Image:
    """Frame (rendered at HEIGHT - BANNER_H) on top, a banner with step text, legend and local time below."""
    h, w = frame.image.shape[:2]
    im = Image.new("RGB", (w, h + BANNER_H), (6, 7, 12))
    im.paste(Image.fromarray(frame.image), (0, 0))
    d = ImageDraw.Draw(im)
    big, small = _font(22), _font(15)
    y0 = h + 8
    d.text((16, y0), title, fill=(235, 238, 245), font=big)
    d.text((16, y0 + 30), subtitle, fill=(150, 156, 170), font=small)
    x = w - 16
    stamp = when.strftime("%Y-%m-%d %H:%M:%S")
    tw = d.textlength(stamp, font=small)
    d.text((x - tw, y0 + 30), stamp, fill=(150, 156, 170), font=small)
    for rgb, label in reversed(legend):
        tw = d.textlength(label, font=small)
        x -= tw
        d.text((x, y0 + 4), label, fill=(210, 214, 222), font=small)
        x -= 22
        d.rectangle((x, y0 + 6, x + 14, y0 + 20), fill=rgb)
        x -= 18
    if badge:
        draw_badge(im, badge, badge_rgb)
    return im


BADGE_W = 170
PROPOSED_RGB = (255, 184, 0)
ACCEPTED_RGB = (46, 204, 113)
REJECTED_RGB = (130, 134, 145)


def draw_badge(im: Image.Image, text: str, rgb: tuple[int, int, int]) -> None:
    """Fixed-size badge in the top-right corner (fixed so a later decision badge fully covers the PROPOSED one)."""
    d = ImageDraw.Draw(im)
    big = _font(22)
    w = im.width
    d.rectangle((w - 16 - BADGE_W, 12, w - 16, 46), fill=rgb)
    tw = d.textlength(text, font=big)
    d.text((w - 16 - BADGE_W + (BADGE_W - tw) / 2, 15), text, fill=(10, 10, 14), font=big)
