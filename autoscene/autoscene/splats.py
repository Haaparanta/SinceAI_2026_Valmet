"""The real splats of the scan, cached as a compact SH-0 array, and an SH-0 PLY writer.

Every row index used by the step-by-step build is a row of the source PLY (0 .. real_rows-1), the same index space as
`src_index` in clean.npz. Parts store these indices; their .ply files are rebuilt from them.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from autoscene.orientation import to_world
from autoscene.ply_io import SH_C0, load_gaussians
from autoscene.splat_rows import real_row_count

log = logging.getLogger("stepbuild.splats")

# INRIA names, standard order without normals and higher SH: what SuperSplat / three.js splat loaders read by name.
SH0_FIELDS = (
    "x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
    "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3",
)
SH0_DTYPE = np.dtype([(f, "<f4") for f in SH0_FIELDS])


def load_real_splats(ply: Path, cache: Path) -> np.ndarray:
    """Structured SH0_DTYPE array of the real rows in the world frame (common/orientation.py: the stored scan is
    rotated 180 deg about z); cached as .npy (28 MB). Name the cache after orientation.FRAME so a changed transform
    never reuses a stale cache."""
    if cache.exists() and cache.stat().st_mtime >= ply.stat().st_mtime:
        return np.load(cache)
    g = load_gaussians(str(ply))
    n_real, _ = real_row_count(g)
    out = np.empty(n_real, dtype=SH0_DTYPE)
    for f in SH0_FIELDS:
        out[f] = g[f][:n_real]
    out = to_world(out)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, out)
    log.info("cached %s real splats (of %s header rows) -> %s", f"{n_real:,}", f"{len(g):,}", cache)
    return out


def xyz_of(s: np.ndarray) -> np.ndarray:
    return np.stack([s["x"], s["y"], s["z"]], 1).astype(np.float32)


def rgb_of(s: np.ndarray) -> np.ndarray:
    """uint8 RGB from the degree-0 SH colour (clamped)."""
    dc = np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], 1)
    return np.rint(np.clip(0.5 + SH_C0 * dc, 0.0, 1.0) * 255.0).astype(np.uint8)


def size_of(s: np.ndarray, lo: float = 0.008, hi: float = 0.05) -> np.ndarray:
    """Render footprint per splat: 1.5 x its longest linear scale, clamped to [lo, hi] scene units, then shrunk for
    see-through splats (x clip(2 alpha, 0.3, 1)) so fog does not paint big opaque discs."""
    longest = np.exp(np.clip(np.maximum(np.maximum(s["scale_0"], s["scale_1"]), s["scale_2"]), -30, 0))
    see_through = np.clip(2.0 * alpha_of(s), 0.3, 1.0)
    return (np.clip(1.5 * longest, lo, hi) * see_through).astype(np.float32)


def alpha_of(s: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(s["opacity"], -30, 30)))).astype(np.float32)


def write_sh0_ply(path: Path, splats: np.ndarray, comment: str = "") -> None:
    """Binary little-endian 3DGS PLY with the 14 SH0_FIELDS. Zero rows is allowed (the empty starting state)."""
    header = ["ply", "format binary_little_endian 1.0", "comment a2b step-by-step build (SH degree 0)"]
    if comment:
        header.append(f"comment {comment}")
    header.append(f"element vertex {len(splats)}")
    header += [f"property float {f}" for f in SH0_FIELDS]
    header.append("end_header")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(("\n".join(header) + "\n").encode("ascii"))
        fh.write(np.ascontiguousarray(splats, dtype=SH0_DTYPE).tobytes())
    tmp.replace(path)
