"""Part detectors (Step 3+). Each one looks only at the current pool and returns which pool points form the next
part, plus its name, text and camera. Nothing joins current.ply until a human accepts it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from sklearn.cluster import DBSCAN

from stepbuild import render as R
from stepbuild.geometry import ceiling_height_by_cells, ceiling_split, envelope_edge, fit_floor_plane
from stepbuild.splats import alpha_of, rgb_of


@dataclass
class PartProposal:
    take: np.ndarray                        # bool over the pool arrays passed in
    name: str                               # file-safe: floor, ceiling, wall_back, ...
    label: str                              # human label
    kind: str                               # structure | pipe | equipment | other
    title: str
    subtitle: str
    camera: R.Camera
    params: dict = field(default_factory=dict)
    info: dict = field(default_factory=dict)
    view_dir: tuple[float, float, float] = (0.0, -0.35, -1.0)  # close-up looks this way (default: from above front)
    # planes y = a*x + b*z + c drawn as lines in the axis views: (label, a, b, c, rgb)
    guides: list[tuple[str, float, float, float, tuple[int, int, int]]] = field(default_factory=list)


def floor(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
          above: float = 0.025) -> PartProposal:
    """The floor: every pool point at or below the fitted floor plane + `above` (about 2 x its RMS thickness). The
    plane is fitted (geometry.fit_floor_plane), not flat: the Equipment Room floor tilts ~5 cm across the room, and a
    flat cut took up to 5 cm of the objects standing on its low side (rejected by the user, image 0225)."""
    a, b, c, rms = fit_floor_plane(xyz)
    plane_y = a * xyz[:, 0] + b * xyz[:, 2] + c
    take = xyz[:, 1] <= plane_y + above
    n = int(take.sum())
    pts = xyz[take]
    lo, hi = (pts.min(0), pts.max(0)) if n else (bmin, bmax)
    tilt = float(np.degrees(np.arctan(np.hypot(a, b))))
    corners = [a * x + b * z + c for x in (bmin[0], bmax[0]) for z in (bmin[2], bmax[2])]
    return PartProposal(
        take=take, name="floor", label="Floor", kind="structure",
        title=f"FLOOR (tilted plane + {100 * above:.1f} cm)",
        subtitle=(f"floor plane y = {a:+.4f} x {b:+.4f} z {c:+.3f} (tilt {tilt:.2f} deg, y {min(corners):+.3f}…"
                  f"{max(corners):+.3f}, rms {100 * rms:.1f} cm) · {n:,} of {len(xyz):,} pool points "
                  f"({100 * n / len(xyz):.1f} %) · x {lo[0]:+.1f}…{hi[0]:+.1f}, z {lo[2]:+.1f}…{hi[2]:+.1f}"),
        camera=R.overview_camera(bmin, bmax),
        params={"above": above},
        info={"plane": [round(a, 6), round(b, 6), round(c, 5)], "rms": round(rms, 4), "tilt_deg": round(tilt, 3)},
        guides=[("floor plane", a, b, c, (90, 200, 255)), (f"cut +{100 * above:.1f} cm", a, b, c + above,
                                                           (255, 200, 0))],
    )


def ceiling(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray, white: int = 240,
            below: float = 0.03, lift: float = 0.0, lo: float = 0.0, hi: float = 0.0) -> PartProposal:
    """The real ceiling: the flat height where most points are (geometry.ceiling_height_by_cells: per 25 cm patch
    the highest dense layer, so pipes running just under the ceiling never count), and everything from `below`
    under that height upwards: nothing up there can be a pipe. Saturated-white points (min RGB >= `white`) are the
    lamps and are left for their own part. Close-up from below.

    `lift` raises the cut by hand (the user asked for +5..10 cm after 0057); `lo`/`hi` (both set) take exactly that
    height band instead (the user picked 1.50..1.60 after the probe images).

    Rejected by the user: 0046 (everything above the gap over the pipe band, y 1.13: took pipes running next to the
    ceiling) and 0057 (cut at 1.27: still too close to it)."""
    split_y, _ = ceiling_split(xyz[:, 1])
    lamp = (xyz[:, 1] >= split_y) & (rgb_of(pool).min(1) >= white)
    ceiling_y, cells, cells_near = ceiling_height_by_cells(xyz[~lamp], split_y)  # lamps hang lower: no vote
    manual = hi > lo != 0.0
    cut = lo if manual else ceiling_y - below + lift
    take = (xyz[:, 1] >= cut) & ~lamp
    if manual:
        take &= xyz[:, 1] <= hi
    n = int(take.sum())
    return PartProposal(
        take=take, name="ceiling", label="Ceiling", kind="structure",
        title=(f"CEILING (band y {lo:+.2f}…{hi:+.2f}, picked by hand)" if manual else
               f"CEILING (from y {cut:+.2f} up)" + (f", raised {100 * lift:.0f} cm" if lift else "")),
        subtitle=((f"height band picked by hand · {n:,} points (white lamp points left out)")
                  if manual else
                  (f"flat ceiling y {ceiling_y:+.3f} in {cells_near} of {cells} patches · pipes under it stay · "
                   f"{n:,} points · {int(lamp.sum()):,} white lamp points left for their own part")),
        camera=R.look_up_camera(bmin, bmax, ceiling_y),
        params={"white": white, "below": below, "lift": lift, "lo": lo, "hi": hi},
        info={"ceiling_y": round(ceiling_y, 4), "cut_y": round(cut, 4), "patches": cells,
              "patches_at_ceiling": cells_near, "lamp_points": int(lamp.sum())},
        view_dir=(0.0, 0.55, -1.0),
        guides=([(f"band bottom y {lo:+.2f}", 0.0, 0.0, lo, (255, 200, 0)),
                 (f"band top y {hi:+.2f}", 0.0, 0.0, hi, (90, 200, 255))] if manual else
                [(f"cut y {cut:+.2f}", 0.0, 0.0, cut, (255, 200, 0))]),
    )


def lamp(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray, white: int = 240,
         min_y: float = 1.13, eps: float = 0.04, min_samples: int = 8, number: int = 1) -> PartProposal:
    """One lamp per step: the largest cluster (DBSCAN, eps 4 cm) of saturated-white points (min RGB >= `white`) up
    at the ceiling (y >= `min_y`, above the pipes). The fluorescent tubes hang in a row along x at z ~ -2.45; the
    next call proposes the next largest. Close-up from below."""
    cand = np.flatnonzero((xyz[:, 1] >= min_y) & (rgb_of(pool).min(1) >= white))
    take = np.zeros(len(xyz), dtype=bool)
    info: dict = {"white_candidates": len(cand)}
    if len(cand):
        lab = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(xyz[cand])
        ids, cnt = np.unique(lab[lab >= 0], return_counts=True)
        if len(ids):
            take[cand[lab == ids[int(np.argmax(cnt))]]] = True
            info.update(clusters=len(ids), sizes=sorted(cnt.tolist(), reverse=True)[:8], noise=int((lab < 0).sum()))
    n = int(take.sum())
    pts = xyz[take] if n else xyz[:1]
    lo, hi = pts.min(0), pts.max(0)
    size = hi - lo
    return PartProposal(
        take=take, name=f"lamp_{number}", label=f"Lamp {number}", kind="equipment",
        title=f"LAMP {number} (white cluster at the ceiling)",
        subtitle=(f"{n:,} white points · {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} u · x {lo[0]:+.2f}…{hi[0]:+.2f}, "
                  f"y {lo[1]:+.2f}…{hi[1]:+.2f}, z {lo[2]:+.2f}…{hi[2]:+.2f} · largest of "
                  f"{info.get('clusters', 0)} white clusters"),
        camera=R.look_up_from_middle(bmin, bmax, -0.17),
        params={"white": white, "min_y": min_y, "eps": eps, "min_samples": min_samples},
        info=info,
        view_dir=(0.0, 0.55, -1.0),
    )


WALLS = {  # side: (depth axis, run axis, sign: wall at the LOW end of sign * coordinate, close-up view direction)
    "back": (2, 0, 1.0, (0.0, -0.25, -1.0)), "front": (2, 0, -1.0, (0.0, -0.25, 1.0)),
    "left": (0, 2, 1.0, (-1.0, -0.25, 0.0)), "right": (0, 2, -1.0, (1.0, -0.25, 0.0)),
}


def wall(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
         side: str = "back", thick: float = 0.035, strip: float = 0.25, window: float = 0.15) -> PartProposal:
    """One wall (`side` = back | front | left | right). The room's outer face comes from geometry.envelope_edge; per
    `strip` along the wall the wall's main layer is the densest 1 cm slab within `window` inside that face (so
    equipment along the wall, 20+ cm in, never counts). The wall = every pool point from the outer face up to
    `thick` past the main layer (the layer is ~2 cm rms)."""
    if side not in WALLS:
        raise ValueError(f"side must be one of {sorted(WALLS)}")
    ax, run_ax, sign, view = WALLS[side]
    depth = sign * xyz[:, ax]
    face = sign * envelope_edge(xyz[:, ax], high=sign < 0)            # outer face, in depth coordinates
    run = xyz[:, run_ax]
    edges = np.arange(np.floor(np.percentile(run, 0.5) / strip) * strip, np.percentile(run, 99.5) + strip, strip)
    near = (depth >= face - 0.05) & (depth <= face + window)
    surf = np.full(len(edges) - 1, np.nan)
    for i in range(len(surf)):                                       # densest 1 cm layer near the face, per strip
        sel = near & (run >= edges[i]) & (run < edges[i + 1])
        if sel.sum() >= 50:
            h, e = np.histogram(depth[sel], bins=np.arange(face - 0.05, face + window + 0.01, 0.01))
            h = np.convolve(h, np.ones(3) / 3, mode="same")
            surf[i] = e[int(np.argmax(h))] + 0.005
    fill = float(np.nanmedian(surf))
    surf = np.where(np.isnan(surf), fill, surf)
    k = np.clip(np.searchsorted(edges, run, side="right") - 1, 0, len(surf) - 1)
    take = depth <= surf[k] + thick
    n = int(take.sum())
    axis = "xyz"[ax]
    wall_med = sign * fill
    prof_depth = surf
    return PartProposal(
        take=take, name=f"wall_{side}", label=f"{side.capitalize()} wall", kind="structure",
        title=f"{side.upper()} WALL ({axis} {wall_med:+.2f}, {100 * thick:.1f} cm into the room)",
        subtitle=(f"main wall layer {axis} {wall_med:+.3f} (per 25 cm strip, range {sign * prof_depth.max():+.2f}…"
                  f"{sign * prof_depth.min():+.2f}) · outer face {sign * face:+.2f} · {n:,} of {len(xyz):,} pool points"),
        camera=R.overview_camera(bmin, bmax),
        params={"side": side, "thick": thick, "strip": strip, "window": window},
        info={"main_layer_median": round(wall_med, 4), "outer_face": round(float(sign * face), 4),
              "profile": [[round(float(a), 3), round(float(sign * d), 4)] for a, d in zip(edges[:-1], prof_depth)]},
        view_dir=view,
    )


def equipment(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray, x: float, y: float, z: float,
              radius: float = 0.8, label: str = "Equipment", cls: str = "other", voxel: float = 0.04,
              min_alpha: float = 0.15, min_per_voxel: int = 3, y_top: float = 0.62, number: int = 1) -> PartProposal:
    """One technical object grown from a seed point (x, y, z): pool points with opacity >= `min_alpha`, below
    `y_top` (under the ceiling pipe band) and within `radius` of the seed are put on a `voxel` grid (a voxel counts
    with >= `min_per_voxel` points); the 26-connected group of voxels nearest the seed is the object, and all pool
    points in those voxels belong to it. `cls` is the xlsx asset class (PROCESS_PUMP, CONTROL_VALVE, ...) or a
    generic one (tank, pipe, cabinet, other)."""
    from scipy import ndimage

    seed = np.array([x, y, z], dtype=np.float64)
    near = (np.linalg.norm(xyz - seed, axis=1) <= radius) & (xyz[:, 1] < y_top)
    solid = near & (alpha_of(pool) >= min_alpha)
    take = np.zeros(len(xyz), dtype=bool)
    info: dict = {"seed": [x, y, z]}
    if solid.sum():
        o = xyz[near].min(0)
        k_all = np.floor((xyz[near] - o) / voxel).astype(int)
        k_sol = np.floor((xyz[solid] - o) / voxel).astype(int)
        dims = k_all.max(0) + 1
        grid = np.zeros(dims, np.int32)
        np.add.at(grid, tuple(k_sol.T), 1)
        lab, n = ndimage.label(grid >= min_per_voxel, structure=np.ones((3, 3, 3)))
        occ = np.argwhere(lab > 0)
        if len(occ):
            sk = np.floor((seed - o) / voxel)
            nearest = occ[np.argmin(np.linalg.norm(occ - sk, axis=1))]
            comp = lab[tuple(nearest)]
            in_comp = lab[tuple(k_all.T)] == comp
            take[np.flatnonzero(near)[in_comp]] = True
            info.update(components=int(n), voxels=int((lab == comp).sum()))
    pts = xyz[take] if take.any() else seed[None, :]
    lo, hi = np.percentile(pts, 1, axis=0), np.percentile(pts, 99, axis=0)
    size = hi - lo
    name = "".join(c if c.isalnum() else "_" for c in str(cls).lower())
    return PartProposal(
        take=take, name=f"{name}_{number}", label=f"{label} {number}", kind="equipment",
        title=f"{str(label).upper()} {number} ({cls})",
        subtitle=(f"{int(take.sum()):,} points · {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} u · centre "
                  f"({(lo[0] + hi[0]) / 2:+.2f}, {(lo[1] + hi[1]) / 2:+.2f}, {(lo[2] + hi[2]) / 2:+.2f}) · grown from the seed "
                  f"({x:+.2f}, {y:+.2f}, {z:+.2f}) within {radius:.1f} u"),
        camera=R.overview_camera(bmin, bmax),
        params={"x": x, "y": y, "z": z, "radius": radius, "label": label, "cls": cls, "voxel": voxel,
                "min_alpha": min_alpha, "min_per_voxel": min_per_voxel, "y_top": y_top},
        info=info,
    )


DETECTORS: dict[str, Callable[..., PartProposal]] = {
    "floor": floor,
    "ceiling": ceiling,
    "lamp": lamp,
    "wall": wall,
    "equipment": equipment,
}
