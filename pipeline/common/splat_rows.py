"""Find where the real splats end in a 3DGS PLY whose header count is too big.

The boiler-room PLY declares 1,506,136 vertices, but only rows 0 .. 502,481 are trained splats; the rest are random
bits (analysis/ply_study/README.md S2). A real row has every field finite and small, a unit quaternion and a sane
log-scale, and the real rows form one contiguous run from row 0. `real_row_count` returns the length of that run, so a file
without a garbage tail comes back unchanged.
"""

from __future__ import annotations

import numpy as np

QUAT_FIELDS = ("rot_0", "rot_1", "rot_2", "rot_3")
SCALE_FIELDS = ("scale_0", "scale_1", "scale_2")


def row_is_plausible(g: np.ndarray, quat_tol: float = 1e-4, max_abs: float = 1e3) -> np.ndarray:
    """Per-row bool: every field finite with |v| < max_abs, |q| = 1 +- quat_tol, -30 <= log-scale <= 1.

    Checking every field matters: the last row before the boiler-room tail (502,482) is half-written, with real
    position/scale/rotation/colour but SH coefficients around 1e28."""
    ok = np.ones(len(g), dtype=bool)
    with np.errstate(invalid="ignore", over="ignore"):
        for name in g.dtype.names:  # field by field: no 1.5 M x 59 temporary; NaN fails the comparison
            ok &= np.abs(g[name]) < max_abs
        q2 = sum(g[f].astype(np.float64) ** 2 for f in QUAT_FIELDS)
        ok &= np.abs(np.sqrt(q2) - 1.0) < quat_tol
        for f in SCALE_FIELDS:
            ok &= (g[f] >= -30.0) & (g[f] <= 1.0)
    return ok


def real_row_count(g: np.ndarray) -> tuple[int, int]:
    """Return (n_real, plausible_after): the length of the plausible prefix, and how many rows after it still look
    plausible (should be ~0 for an exporter garbage tail; a large number means the data is not a clean prefix)."""
    ok = row_is_plausible(g)
    bad = np.flatnonzero(~ok)
    n_real = int(bad[0]) if len(bad) else len(g)
    return n_real, int(ok[n_real:].sum())
