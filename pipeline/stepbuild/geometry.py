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
                      max_forward: float = 0.03, anchor: float | None = None) -> WallProfile:
    """Wall at the low end of `depth` (the back wall: low z). Global depth = densest thin slab in the back half of
    the p0.5..p99.5 depth range, so the room must lie in front of the wall (true for a scan taken inside the room).
    Per strip of `run`: among histogram bins within `window` of the global depth, the back-most bin holding at least
    `rel` x the strip's peak is the wall; equipment in front is denser in some strips, floaters behind are diffuse.
    A strip may sit deeper than the global wall (a recess); a strip more than `max_forward` in front of it is not
    believed and gets the global depth: where equipment hides the wall (the right-hand corner of the scan) the
    back-most dense layer is the equipment, and cutting behind it would delete real wall points."""
    if anchor is None:
        lo, hi = np.percentile(depth, [0.5, 99.5])
        counts, e = np.histogram(depth, bins=np.arange(lo, 0.5 * (lo + hi) + bin_size, bin_size))
        g = 0.5 * (e[np.argmax(counts)] + e[np.argmax(counts) + 1])
    else:                                                     # caller knows roughly where the wall is
        g = anchor
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
    smooth = np.where(smooth > g + max_forward, g, smooth)
    return WallProfile(edges=edges, depth=smooth, measured=measured, global_depth=g)


def outer_edge(values: np.ndarray, bin_size: float = 0.05, rel: float = 0.05) -> float:
    """High-side edge of a dense block of points along one axis: walking outward from the densest bin on the high
    half, the first bin holding less than `rel` x that peak. Sparse strays beyond it are outside the room."""
    return outer_edge_gap(values, bin_size, rel)[0]


def outer_edge_gap(values: np.ndarray, bin_size: float = 0.05, rel: float = 0.05) -> tuple[float, float]:
    """(edge, gap): the outer_edge and how far it lies past the densest bin. A small gap means a sharp wall; a large
    gap means the scan just thins out (real clutter, not a boundary)."""
    lo, hi = np.percentile(values, 50), values.max()
    counts, e = np.histogram(values, bins=np.arange(lo, hi + bin_size, bin_size))
    k = int(np.argmax(counts))
    below = np.flatnonzero(counts[k:] < rel * counts[k])
    edge = float(e[k + below[0]]) if len(below) else float(e[-1])
    return edge, edge - float(e[k])


def top_layer_edge(y: np.ndarray, bin_size: float = 0.04, rel_peak: float = 0.02, rel_edge: float = 0.10
                   ) -> tuple[float, float]:
    """(ceiling_y, edge_y) for a room whose ceiling is NOT its densest upper layer (pipes hang below it). Ceiling =
    the topmost local maximum of the y histogram holding at least `rel_peak` x the global maximum; edge = walking up
    from it, the first bin under `rel_edge` x the ceiling peak. Points above the edge are strays."""
    lo, hi = np.percentile(y, 50), y.max()
    counts, e = np.histogram(y, bins=np.arange(lo, hi + bin_size, bin_size))
    c = np.convolve(counts, np.ones(3) / 3, mode="same")
    peaks = [i for i in range(1, len(c) - 1) if c[i] >= c[i - 1] and c[i] >= c[i + 1] and c[i] >= rel_peak * c.max()]
    k = peaks[-1] if peaks else int(np.argmax(c))
    ceiling = float(0.5 * (e[k] + e[k + 1]))
    above = np.flatnonzero(c[k:] < rel_edge * c[k])
    edge = float(e[k + above[0]]) if len(above) else float(e[-1])
    return ceiling, edge


def ceiling_split(y: np.ndarray, bin_size: float = 0.02) -> tuple[float, float]:
    """(split_y, ceiling_y): the emptiest height between the densest upper layer (the pipe band) and the topmost
    dense layer (the real ceiling). Everything at or above split_y belongs to the ceiling zone."""
    ceiling_y, _ = top_layer_edge(y)
    lo = np.percentile(y, 50)
    counts, e = np.histogram(y, bins=np.arange(lo, ceiling_y + bin_size, bin_size))
    k_max = int(np.argmax(counts))
    seg = counts[k_max:]
    k = k_max + int(np.argmin(seg)) if len(seg) else k_max
    return float(e[k]), ceiling_y


def ceiling_height_by_cells(xyz: np.ndarray, zone_lo: float, cell: float = 0.25, bin_size: float = 0.02,
                            min_points: int = 30) -> tuple[float, int, int]:
    """(ceiling_y, cells, cells_near): the flat ceiling height where pipes run just below it. In every `cell` x
    `cell` patch of the plan (points above `zone_lo` only), take the HIGHEST height bin that still holds half the
    patch's peak: a pipe hanging below the ceiling is lower, so it never wins. The ceiling is the most common of
    those per-patch heights, refined to the median of the patches within 4 cm of it."""
    sel = xyz[:, 1] >= zone_lo
    p = xyz[sel]
    keys = np.floor(p[:, 0] / cell) * 100003 + np.floor(p[:, 2] / cell)
    order = np.argsort(keys)
    keys, ys = keys[order], p[order, 1]
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    ends = np.r_[starts[1:], len(keys)]
    edges = np.arange(zone_lo, ys.max() + 2 * bin_size, bin_size)
    tops = []
    for a, b in zip(starts, ends):
        if b - a < min_points:
            continue
        h = np.convolve(np.histogram(ys[a:b], bins=edges)[0], np.ones(3), mode="same")
        top = np.flatnonzero(h >= 0.5 * h.max())[-1]
        tops.append(edges[top] + 0.5 * bin_size)
    tops = np.asarray(tops)
    h, e = np.histogram(tops, bins=np.arange(zone_lo, tops.max() + 2 * bin_size, bin_size))
    mode = e[int(np.argmax(np.convolve(h, np.ones(3), mode="same")))] + 0.5 * bin_size
    near = np.abs(tops - mode) <= 0.04
    return float(np.median(tops[near])), len(tops), int(near.sum())


def envelope_edge(values: np.ndarray, high: bool, bin_size: float = 0.04, band: float = 0.6, rel: float = 0.25,
                  outer_pct: float = 0.1) -> float:
    """Outer surface of the room on one side of one axis, found from OUTSIDE: start at the p99.9 (or p0.1) value,
    look at the outermost `band` of the data, and walk inward to the first `bin_size` bin holding at least `rel` x
    the densest bin of that band (the wall / ceiling / floor layer). Returns the outer side of that bin. Unlike
    outer_edge this does not start from the densest layer of the whole half, so equipment inside the room never
    decides where the wall is."""
    v = values if high else -values
    outer = float(np.percentile(v, 100 - outer_pct))
    edges = np.arange(outer - band, outer + bin_size, bin_size)
    counts, e = np.histogram(v, bins=edges)
    ok = np.flatnonzero(counts >= rel * counts.max())
    edge = float(e[ok[-1] + 1])
    return edge if high else -edge


def fit_floor_plane(xyz: np.ndarray, band: float = 0.04, iterations: int = 4) -> tuple[float, float, float, float]:
    """(a, b, c, rms) of the floor plane y = a*x + b*z + c: start from the densest low slab (horizontal_plane), take
    the points within `band` of it and fit by least squares, re-fitting on the inliers (|residual| < 2.5 rms). The
    Equipment Room floor is tilted ~0.3 deg (5 cm across the room), so a flat cut is too high on one side."""
    y0 = horizontal_plane(xyz[:, 1], lower=True).y
    sel = np.abs(xyz[:, 1] - y0) <= band
    p = xyz[sel]
    a = b = 0.0
    c = y0
    rms = band
    for _ in range(iterations):
        A = np.c_[p[:, 0], p[:, 2], np.ones(len(p))]
        (a, b, c), *_ = np.linalg.lstsq(A, p[:, 1], rcond=None)
        r = p[:, 1] - A @ np.array([a, b, c])
        rms = float(np.sqrt(np.mean(r ** 2)))
        p = p[np.abs(r) < 2.5 * rms]
    return float(a), float(b), float(c), rms
