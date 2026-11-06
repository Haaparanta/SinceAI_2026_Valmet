"""Part detectors (Step 3+). Each one looks only at the current pool and returns which pool points form the next
part, plus its name, text and camera. Nothing joins current.ply until a human accepts it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from stepbuild import render as R
from stepbuild.geometry import ceiling_split, horizontal_plane
from stepbuild.splats import rgb_of


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


def floor(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray | None = None,
          above: float = 0.03) -> PartProposal:
    """The floor slab: every pool point at or below floor_y + `above` (2 x the floor's RMS thickness). Everything
    lower was removed in 2a, so this is the slab itself; objects standing on the floor lose at most their lowest 3 cm.
    Room-scale part: shown from the fixed overview camera instead of the 25 % framing."""
    plane = horizontal_plane(xyz[:, 1], lower=True)
    take = xyz[:, 1] <= plane.y + above
    n = int(take.sum())
    pts = xyz[take]
    lo, hi = (pts.min(0), pts.max(0)) if n else (bmin, bmax)
    return PartProposal(
        take=take, name="floor", label="Floor", kind="structure",
        title=f"FLOOR (y <= {plane.y + above:+.3f})",
        subtitle=(f"floor y {plane.y:+.3f} (rms {100 * plane.rms:.1f} cm) · {n:,} of {len(xyz):,} pool points "
                  f"({100 * n / len(xyz):.1f} %) · x {lo[0]:+.1f}…{hi[0]:+.1f}, z {lo[2]:+.1f}…{hi[2]:+.1f}"),
        camera=R.overview_camera(bmin, bmax),
        params={"above": above},
        info={"floor_y": round(plane.y, 4), "floor_rms": round(plane.rms, 4)},
    )


def _ceiling_zone(xyz: np.ndarray, pool: np.ndarray, white: int) -> tuple[np.ndarray, np.ndarray, float, float]:
    split_y, ceiling_y = ceiling_split(xyz[:, 1])
    zone = xyz[:, 1] >= split_y
    lamp = zone & (rgb_of(pool).min(1) >= white)
    return zone, lamp, split_y, ceiling_y


def ceiling(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray, white: int = 240
            ) -> PartProposal:
    """The real ceiling: every pool point above the gap that separates it from the (denser) pipe band below,
    minus the saturated-white lamp points (min RGB >= `white`), which become their own part. Close-up from below."""
    zone, lamp, split_y, ceiling_y = _ceiling_zone(xyz, pool, white)
    take = zone & ~lamp
    n = int(take.sum())
    pts = xyz[take]
    lo, hi = (pts.min(0), pts.max(0)) if n else (bmin, bmax)
    return PartProposal(
        take=take, name="ceiling", label="Ceiling", kind="structure",
        title=f"CEILING (y >= {split_y:+.2f}, lamps left out)",
        subtitle=(f"ceiling layer y {ceiling_y:+.2f} · gap above the pipes at {split_y:+.2f} · {n:,} points · "
                  f"{int(lamp.sum()):,} white lamp points left for their own part · x {lo[0]:+.1f}…{hi[0]:+.1f}"),
        camera=R.look_up_camera(bmin, bmax, ceiling_y),
        params={"white": white},
        info={"split_y": round(split_y, 4), "ceiling_y": round(ceiling_y, 4), "lamp_points": int(lamp.sum())},
        view_dir=(0.0, 0.55, -1.0),
    )


DETECTORS: dict[str, Callable[..., PartProposal]] = {
    "floor": floor,
    "ceiling": ceiling,
}
