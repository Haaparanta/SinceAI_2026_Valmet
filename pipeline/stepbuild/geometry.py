"""Simple, explainable geometry on splat centres: horizontal planes from the y histogram."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Plane:
    y: float              # height of the plane (median of the points near the histogram peak)
    rms: float            # RMS distance of those points from y
    support: int          # points within +-band of y
    band: float


def horizontal_plane(y: np.ndarray, lower: bool, bin_size: float = 0.01, band: float = 0.03) -> Plane:
    """The densest thin horizontal slab in the lower (floor) or upper (ceiling) half of the p0.5..p99.5 y-range,
    refined to the median of the points within +-band of the peak."""
    lo, hi = np.percentile(y, [0.5, 99.5])
    mid = 0.5 * (lo + hi)
    a, b = (lo, mid) if lower else (mid, hi)
    counts, edges = np.histogram(y, bins=np.arange(a, b + bin_size, bin_size))
    k = int(np.argmax(counts))
    peak = 0.5 * (edges[k] + edges[k + 1])
    near = y[np.abs(y - peak) <= band]
    yc = float(np.median(near))
    near = y[np.abs(y - yc) <= band]
    return Plane(y=float(np.median(near)), rms=float(np.sqrt(np.mean((near - yc) ** 2))), support=len(near),
                 band=band)
