"""The .splat file layout (antimatter15) that the viewer's Splats mode loads with Spark: 32 bytes per Gaussian splat.

    float32 x y z | float32 scale x y z (linear) | uint8 r g b a | uint8 quaternion w x y z (q * 128 + 128)

Shared by scripts/export_viewer_scene.py (manual build) and scripts/export_autoscene_viewer.py (automatic build). Takes
any structured array with the INRIA SH-0 field names (stepbuild.splats.SH0_DTYPE, autoscene.splats.SH0_DTYPE), already
in the world frame, and needs nothing but numpy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SH_C0 = 0.28209479
BYTES_PER_SPLAT = 32


def splat_bytes(s: np.ndarray) -> np.ndarray:
    """(n, 32) uint8 rows in the .splat layout."""
    n = len(s)
    out = np.empty((n, BYTES_PER_SPLAT), np.uint8)
    xyz = np.stack([s["x"], s["y"], s["z"]], 1).astype("<f4")
    out[:, 0:12] = xyz.view(np.uint8).reshape(n, 12)
    log_scale = np.stack([s["scale_0"], s["scale_1"], s["scale_2"]], 1)
    scale = np.exp(np.clip(np.nan_to_num(log_scale, nan=-30.0), -30.0, 4.0)).astype("<f4")
    out[:, 12:24] = scale.view(np.uint8).reshape(n, 12)
    dc = np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], 1)
    out[:, 24:27] = np.rint(np.clip(0.5 + SH_C0 * np.nan_to_num(dc), 0.0, 1.0) * 255.0).astype(np.uint8)
    alpha = 1.0 / (1.0 + np.exp(-np.clip(np.nan_to_num(s["opacity"], nan=-30.0), -30.0, 30.0)))
    out[:, 27] = np.rint(alpha * 255.0).astype(np.uint8)
    q = np.nan_to_num(np.stack([s["rot_0"], s["rot_1"], s["rot_2"], s["rot_3"]], 1).astype(np.float64))  # w x y z
    norm = np.linalg.norm(q, axis=1, keepdims=True)
    q = np.where(norm > 1e-12, q / np.maximum(norm, 1e-12), [1.0, 0.0, 0.0, 0.0])
    out[:, 28:32] = np.clip(np.rint(q * 128.0 + 128.0), 0, 255).astype(np.uint8)
    return out


def write_splat(path: Path, s: np.ndarray) -> None:
    """Write `s` as a .splat file (atomically, via a .tmp next to it)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(splat_bytes(s).tobytes())
    tmp.replace(path)
