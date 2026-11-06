"""Cleaning filters (Step 2). Each one looks only at the current pool and returns which pool points it would remove,
plus the text and camera for its image. Nothing is removed until a human accepts the proposal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from stepbuild import render as R
from stepbuild.geometry import horizontal_plane


@dataclass
class CleanProposal:
    remove: np.ndarray                      # bool over the pool arrays passed in
    title: str                              # short, goes after "<index> · CLEAN ·"
    subtitle: str
    camera: R.Camera
    params: dict = field(default_factory=dict)
    info: dict = field(default_factory=dict)


def below_floor(xyz: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, margin: float = 0.04) -> CleanProposal:
    """2a: mirror images of the room under the glossy floor. Remove everything more than `margin` below the floor
    plane (floor = densest thin y-slab in the lower half; its RMS thickness is ~2 cm)."""
    floor = horizontal_plane(xyz[:, 1], lower=True)
    cut = floor.y - margin
    remove = xyz[:, 1] < cut
    depth = floor.y - xyz[remove, 1]
    cam = R.front_elevation_camera(bmin, bmax, eye_y=floor.y)
    n = int(remove.sum())
    return CleanProposal(
        remove=remove,
        title=f"below-floor reflections (y < {cut:+.3f})",
        subtitle=(f"floor y {floor.y:+.3f} (rms {100 * floor.rms:.1f} cm) · remove {n:,} of {len(xyz):,} "
                  f"({100 * n / len(xyz):.1f} %) · median {100 * float(np.median(depth)) if n else 0:.0f} cm below"),
        camera=cam,
        params={"margin": margin},
        info={"floor_y": round(floor.y, 4), "floor_rms": round(floor.rms, 4), "floor_support": floor.support,
              "cut_y": round(cut, 4), "median_depth": round(float(np.median(depth)), 4) if n else 0.0},
    )


CLEANERS: dict[str, Callable[..., CleanProposal]] = {
    "below_floor": below_floor,
}
