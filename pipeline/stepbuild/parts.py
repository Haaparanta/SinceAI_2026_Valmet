"""Part detectors (Step 3+). Each one looks only at the current pool and returns which pool points form the next
part, plus its name, text and camera. Nothing joins current.ply until a human accepts it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from stepbuild import render as R
from stepbuild.geometry import ceiling_height_by_cells, ceiling_split, horizontal_plane
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


def ceiling(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, *, pool: np.ndarray, white: int = 240,
            below: float = 0.03, lift: float = 0.0) -> PartProposal:
    """The real ceiling: the flat height where most points are (geometry.ceiling_height_by_cells: per 25 cm patch
    the highest dense layer, so pipes running just under the ceiling never count), and everything from `below`
    under that height upwards: nothing up there can be a pipe. Saturated-white points (min RGB >= `white`) are the
    lamps and are left for their own part. Close-up from below.

    `lift` raises the cut by hand (the user asked for +5..10 cm after 0057).

    Rejected by the user: 0046 (everything above the gap over the pipe band, y 1.13: took pipes running next to the
    ceiling) and 0057 (cut at 1.27: still too close to it)."""
    split_y, _ = ceiling_split(xyz[:, 1])
    lamp = (xyz[:, 1] >= split_y) & (rgb_of(pool).min(1) >= white)
    ceiling_y, cells, cells_near = ceiling_height_by_cells(xyz[~lamp], split_y)  # lamps hang lower: no vote
    cut = ceiling_y - below + lift
    take = (xyz[:, 1] >= cut) & ~lamp
    n = int(take.sum())
    return PartProposal(
        take=take, name="ceiling", label="Ceiling", kind="structure",
        title=f"CEILING (from y {cut:+.2f} up)" + (f", raised {100 * lift:.0f} cm" if lift else ""),
        subtitle=(f"flat ceiling y {ceiling_y:+.3f} in {cells_near} of {cells} patches · pipes under it stay · "
                  f"{n:,} points · {int(lamp.sum()):,} white lamp points left for their own part"),
        camera=R.look_up_camera(bmin, bmax, ceiling_y),
        params={"white": white, "below": below, "lift": lift},
        info={"ceiling_y": round(ceiling_y, 4), "cut_y": round(cut, 4), "patches": cells,
              "patches_at_ceiling": cells_near, "lamp_points": int(lamp.sum())},
        view_dir=(0.0, 0.55, -1.0),
    )


DETECTORS: dict[str, Callable[..., PartProposal]] = {
    "floor": floor,
    "ceiling": ceiling,
}
