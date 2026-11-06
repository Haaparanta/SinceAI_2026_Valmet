"""Part detectors (Step 3+). Each one looks only at the current pool and returns which pool points form the next
part, plus its name, text and camera. Nothing joins current.ply until a human accepts it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from stepbuild import render as R
from stepbuild.geometry import horizontal_plane


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


DETECTORS: dict[str, Callable[..., PartProposal]] = {
    "floor": floor,
}
