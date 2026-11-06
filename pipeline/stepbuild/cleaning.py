"""Cleaning filters (Step 2). Each one looks only at the current pool and returns which pool points it would remove,
plus the text and camera for its image. Nothing is removed until a human accepts the proposal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from stepbuild import render as R
from stepbuild.geometry import back_wall_profile, horizontal_plane, outer_edge_gap, top_layer_edge
from stepbuild.splats import alpha_of


@dataclass
class CleanProposal:
    remove: np.ndarray                      # bool over the pool arrays passed in
    title: str                              # short, goes after "<index> · CLEAN ·"
    subtitle: str
    camera: R.Camera
    params: dict = field(default_factory=dict)
    info: dict = field(default_factory=dict)
    hide_kept: np.ndarray | None = None     # bool over the pool: kept points left out of this image only (view cut)
    removed_size: float | None = None       # draw removed points at this fixed size (small, sparse points)
    what: str = ""                          # the change in plain words, for the image headline


def below_floor(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
                margin: float = 0.04) -> CleanProposal:
    """2a: mirror images of the room under the glossy floor. Remove everything more than `margin` below the floor
    plane (floor = densest thin y-slab in the lower half; its RMS thickness is ~2 cm)."""
    floor = horizontal_plane(xyz[:, 1], lower=True)
    cut = floor.y - margin
    remove = xyz[:, 1] < cut
    depth = floor.y - xyz[remove, 1]
    cam = R.front_elevation_camera(bmin, bmax, eye_y=floor.y)
    n = int(remove.sum())
    return CleanProposal(
        what="reflections under the floor",
        remove=remove,
        title=f"below-floor reflections (y < {cut:+.3f})",
        subtitle=(f"floor y {floor.y:+.3f} (rms {100 * floor.rms:.1f} cm) · remove {n:,} of {len(xyz):,} "
                  f"({100 * n / len(xyz):.1f} %) · median {100 * float(np.median(depth)) if n else 0:.0f} cm below"),
        camera=cam,
        params={"margin": margin},
        info={"floor_y": round(floor.y, 4), "floor_rms": round(floor.rms, 4), "floor_support": floor.support,
              "cut_y": round(cut, 4), "median_depth": round(float(np.median(depth)), 4) if n else 0.0},
    )


def behind_back_wall(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
                     margin: float = 0.04, strip: float = 0.25, hide_above: float = 0.9) -> CleanProposal:
    """2b: floaters behind the back wall. The wall depth (z) is found per `strip` of x, so the cut follows the recess
    between x -1.6 and 0; remove z < wall(x) - margin. Image: plan view from above with kept points above
    `hide_above` (ceiling band) hidden, so the wall line and the room behind the red cut are visible."""
    prof = back_wall_profile(xyz[:, 0], xyz[:, 2], strip=strip)
    wall = prof.at(xyz[:, 0])
    remove = xyz[:, 2] < wall - margin
    n = int(remove.sum())
    zlo = min(float(np.percentile(xyz[remove, 2], 2)) if n else bmin[2], prof.global_depth - 0.6)
    cam = R.top_down_camera(np.array([bmin[0], 0, zlo]), np.array([bmax[0], 0, bmax[2]]), eye_y=bmax[1] + 1.0)
    recess = prof.depth < prof.global_depth - 0.03
    rx = (f"recess {prof.depth[recess].mean():+.2f} at x {prof.edges[:-1][recess].min():+.1f}…"
          f"{prof.edges[1:][recess].max():+.1f}") if recess.any() else "no recess"
    return CleanProposal(
        what="floaters behind the back wall",
        remove=remove,
        title=f"behind the back wall (z < wall(x) - {margin:.2f})",
        subtitle=(f"wall z {prof.global_depth:+.3f} · {rx} · remove {n:,} of {len(xyz):,} "
                  f"({100 * n / len(xyz):.1f} %) · top view, ceiling hidden"),
        camera=cam,
        params={"margin": margin, "strip": strip},
        info={"wall_z": round(prof.global_depth, 4),
              "profile": [[round(float(a), 3), round(float(d), 4)] for a, d in zip(prof.edges[:-1], prof.depth)]},
        hide_kept=xyz[:, 1] > hide_above,
    )


def floating_fog(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray,
                 max_alpha: float = 0.05, gap: float = 0.05) -> CleanProposal:
    """2c: see-through splats floating in the air. Most low-opacity splats hug real surfaces (median 1.4 cm from a
    solid splat) and are kept; remove only those with alpha < max_alpha AND more than `gap` from every splat with
    alpha >= max_alpha."""
    alpha = alpha_of(pool)
    solid = alpha >= max_alpha
    dist = np.zeros(len(xyz))
    if solid.any() and (~solid).any():
        dist[~solid], _ = cKDTree(xyz[solid]).query(xyz[~solid], k=1)
    remove = ~solid & (dist > gap)
    n, n_see = int(remove.sum()), int((~solid).sum())
    return CleanProposal(
        what="see-through fog floating in the air",
        remove=remove,
        title=f"floating fog (alpha < {max_alpha:g}, > {100 * gap:.0f} cm from solid)",
        subtitle=(f"remove {n:,} of {len(xyz):,} ({100 * n / len(xyz):.1f} %) · keeps {n_see - n:,} see-through "
                  f"splats on surfaces · solid = alpha >= {max_alpha:g}"),
        camera=R.overview_camera(bmin, bmax),
        params={"max_alpha": max_alpha, "gap": gap},
        info={"see_through": n_see, "solid": int(solid.sum()),
              "removed_gap_p50": round(float(np.median(dist[remove])), 4) if n else 0.0},
        removed_size=0.01,
    )


def outside_room(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
                 margin: float = 0.04, max_gap: float = 0.5) -> CleanProposal:
    """Strays above the real ceiling and past the side edges of the room.

    Ceiling: in this room the densest upper layer is the band of insulated pipes (y ~0.88); the real ceiling is the
    weaker layer above it (y ~1.28). So the ceiling is the topmost dense layer and the cut is where the density above
    it falls under 10 % of that layer (geometry.top_layer_edge). Sides: past the outer edge of the dense material on
    each side of x, but only on a side with a sharp wall (edge within `max_gap` of the densest layer): on the other
    side the scan just thins out through real clutter, so nothing is cut there. The open front and the floor are
    handled elsewhere."""
    ceiling_y, top_edge = top_layer_edge(xyz[:, 1])
    hi_x, hi_gap = outer_edge_gap(xyz[:, 0])
    lo_x, lo_gap = outer_edge_gap(-xyz[:, 0])
    lo_x = -lo_x
    hi_x = hi_x if hi_gap <= max_gap else np.inf
    lo_x = lo_x if lo_gap <= max_gap else -np.inf
    above = xyz[:, 1] > top_edge + margin
    side = (xyz[:, 0] > hi_x + margin) | (xyz[:, 0] < lo_x - margin)
    remove = above | side
    n = int(remove.sum())
    cam = R.front_elevation_camera(bmin, bmax, eye_y=top_edge + margin, look_y=0.5 * (bmin[1] + top_edge))
    return CleanProposal(
        what="strays above the ceiling and past the sides",
        remove=remove,
        title=f"outside the room (y > {top_edge + margin:+.2f}, x < {lo_x - margin:+.2f} or > {hi_x + margin:+.2f})"
              .replace("inf", "none"),
        subtitle=(f"ceiling layer y {ceiling_y:+.2f} (pipes below it) · top edge {top_edge:+.2f} · "
                  f"above {int(above.sum()):,} + sides {int((side & ~above).sum()):,} = {n:,} "
                  f"({100 * n / len(xyz):.1f} %) · eye at the cut height"),
        camera=cam,
        params={"margin": margin},
        info={"ceiling_y": round(ceiling_y, 4), "top_edge_y": round(top_edge, 4),
              "x_edges": [None if np.isinf(v) else round(float(v), 4) for v in (lo_x, hi_x)],
              "x_gaps": [round(lo_gap, 3), round(hi_gap, 3)], "above": int(above.sum()),
              "sides_only": int((side & ~above).sum())},
        removed_size=0.012,
    )


WALL_SIDES = {  # side: (depth axis, run axis, sign so that the wall is at the LOW end of sign * coordinate)
    "back": (2, 0, 1.0), "front": (2, 0, -1.0), "left": (0, 2, 1.0), "right": (0, 2, -1.0),
}
WALL_LABEL = {"back": "back wall (-z)", "front": "front wall (+z)", "left": "left wall (-x)", "right": "right wall (+x)"}


def behind_wall(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
                side: str = "back", margin: float = 0.04, strip: float = 0.25, hide_above: float = 0.5,
                max_gap: float = 0.5) -> CleanProposal:
    """Floaters behind one wall (`side` = back | front | left | right). The wall depth is found per `strip` along
    the wall (geometry.back_wall_profile on the mirrored axis), and points more than `margin` behind it go. A side
    whose outer edge is not sharp (more than `max_gap` past its densest layer) has no wall in the scan: the
    detector then raises instead of cutting into the room (the Equipment Room scan has sharp walls only at the back
    and on the left). Image: top view, everything above `hide_above` hidden."""
    if side not in WALL_SIDES:
        raise ValueError(f"side must be one of {sorted(WALL_SIDES)}")
    ax, run_ax, sign = WALL_SIDES[side]
    depth = sign * xyz[:, ax]
    edge, gap = outer_edge_gap(-depth)
    outer = -edge                                    # outer edge of ALL dense material on this side (depth coords)
    if gap > max_gap:
        raise ValueError(f"no sharp {WALL_LABEL[side]} in the scan: its edge lies {gap:.2f} u past the densest layer "
                         f"(a wall is within {max_gap})")
    prof = back_wall_profile(xyz[:, run_ax], depth, strip=strip)
    # never cut inside the outer edge of the dense material: on the Equipment Room's left side a second, 15 cm thick
    # dense layer sits behind the main wall layer, and per-strip walls alone sliced through it (images 0164-0173)
    cut = np.minimum(prof.at(xyz[:, run_ax]), outer) - margin
    remove = depth < cut
    n = int(remove.sum())
    wall = sign * prof.global_depth
    lo, hi = bmin.copy(), bmax.copy()
    if n:
        far = np.percentile(xyz[remove, ax], 2 if sign > 0 else 98)
        lo[ax], hi[ax] = min(lo[ax], far), max(hi[ax], far)
    cam = R.top_down_camera(lo, hi, eye_y=bmax[1] + 1.0)
    wall_med = sign * float(np.median(prof.depth[prof.measured])) if prof.measured.any() else wall
    layers = (f"wall layer {'xyz'[ax]} {wall_med:+.2f} (median of strips, range "
              f"{sign * prof.depth.max():+.2f}…{sign * prof.depth.min():+.2f})"
              + (f"; denser layer in front at {wall:+.2f}" if abs(wall_med - wall) > 0.05 else "")
              + f"; dense material ends at {sign * outer:+.2f}")
    return CleanProposal(
        what=f"floaters behind the {WALL_LABEL[side]}",
        remove=remove,
        title=f"behind the {WALL_LABEL[side]} (wall layer {'xyz'[ax]} {wall_med:+.2f})",
        subtitle=(f"{layers} · cut {100 * margin:.0f} cm behind the wall and the dense material · remove {n:,} of {len(xyz):,} "
                  f"({100 * n / len(xyz):.1f} %) · top view, above y {hide_above:+.1f} hidden"),
        camera=cam,
        params={"side": side, "margin": margin, "strip": strip},
        info={"outer_edge": round(float(sign * outer), 4), "densest_layer": round(float(wall), 4), "wall_layer_median": round(wall_med, 4), "edge_gap": round(float(gap), 3),
              "profile": [[round(float(a), 3), round(float(sign * d), 4)] for a, d in zip(prof.edges[:-1], prof.depth)]},
        hide_kept=xyz[:, 1] > hide_above,
    )


CLEANERS: dict[str, Callable[..., CleanProposal]] = {
    "below_floor": below_floor,
    "behind_back_wall": behind_back_wall,
    "floating_fog": floating_fog,
    "outside_room": outside_room,
    "behind_wall": behind_wall,
}
