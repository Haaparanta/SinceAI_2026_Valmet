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


@dataclass(frozen=True)
class WallProfile:
    """A wall perpendicular to z (or x) whose depth may step along the other axis, e.g. a recess or door."""
    edges: np.ndarray     # strip edges along the run axis
    depth: np.ndarray     # wall depth per strip (back-most dense layer, refined to a median)
    measured: np.ndarray  # bool per strip: True if the strip had enough points, else the global depth was used
    global_depth: float

    def at(self, run: np.ndarray) -> np.ndarray:
        k = np.clip(np.searchsorted(self.edges, run, side="right") - 1, 0, len(self.depth) - 1)
        return self.depth[k]


def back_wall_profile(run: np.ndarray, depth: np.ndarray, strip: float = 0.25, bin_size: float = 0.01,
                      rel: float = 0.35, min_points: int = 150, window: float = 0.5,
                      max_forward: float = 0.03) -> WallProfile:
    """Wall at the low end of `depth` (the back wall: low z). Global depth = densest thin slab in the back half.
    Per strip of `run`: among histogram bins within `window` of the global depth, the back-most bin holding at least
    `rel` x the strip's peak is the wall; equipment in front is denser in some strips, floaters behind are diffuse.
    A strip may sit deeper than the global wall (a recess) but at most `max_forward` in front of it: where equipment
    hides the wall (the right-hand corner of the scan) the back-most dense layer is the equipment, and cutting behind
    it would delete real wall points."""
    lo, hi = np.percentile(depth, [0.5, 99.5])
    counts, e = np.histogram(depth, bins=np.arange(lo, 0.5 * (lo + hi) + bin_size, bin_size))
    g = 0.5 * (e[np.argmax(counts)] + e[np.argmax(counts) + 1])
    g = float(np.median(depth[np.abs(depth - g) <= 0.02]))
    edges = np.arange(np.floor(np.percentile(run, 0.5) / strip) * strip,
                      np.percentile(run, 99.5) + strip, strip)
    out = np.full(len(edges) - 1, g)
    measured = np.zeros(len(out), dtype=bool)
    near = np.abs(depth - g) <= window
    for i in range(len(out)):
        sel = near & (run >= edges[i]) & (run < edges[i + 1])
        if sel.sum() < min_points:
            continue
        h, be = np.histogram(depth[sel], bins=np.arange(g - window, g + window + bin_size, bin_size))
        h = np.convolve(h, np.ones(3) / 3, mode="same")
        k = int(np.flatnonzero(h >= rel * h.max())[0])
        c = 0.5 * (be[k] + be[k + 1])
        out[i] = float(np.median(depth[sel][np.abs(depth[sel] - c) <= 0.02]))
        measured[i] = True
    smooth = out.copy()                                       # 3-strip median removes single-strip outliers
    for i in range(1, len(out) - 1):
        smooth[i] = np.median(out[i - 1:i + 2])
    smooth = np.minimum(smooth, g + max_forward)
    return WallProfile(edges=edges, depth=smooth, measured=measured, global_depth=g)
