"""World orientation of the boiler-room scan.

The PLY is stored rotated 180 degrees about its z axis relative to the room: as stored, the floor is at y = +1.07
and the insulated ceiling pipes at y = -0.91, and left/right are mirrored. Verified 2026-11-06 against the walkthrough
video (door with the poster, red bucket and pallet jack on the floor, roll cage, pipes along the ceiling) after the
user saw the "floor" part come out as pipes. A 180-degree rotation is a proper rotation (no mirroring), so text and
handedness stay right.

World frame after `to_world`: y up, floor y ~ -1.07, back wall z ~ -3.41, the scan's open (camera) side at +z.
"""

from __future__ import annotations

import numpy as np

FRAME = "world-rotz180-v1"   # bump when the transform changes: derived caches are keyed on it


def to_world(g: np.ndarray) -> np.ndarray:
    """Copy of a structured splat array with positions and rotations rotated 180 degrees about z:
    (x, y, z) -> (-x, -y, z) and q' = q_z180 * q, which for q = (w, x, y, z) is (-z, -y, x, w).
    Scales are in the splat's local frame and stay; SH degree 0 colour stays (higher SH would need rotating and
    is not used downstream)."""
    out = g.copy()
    out["x"] = -g["x"]
    out["y"] = -g["y"]
    if all(f in g.dtype.names for f in ("rot_0", "rot_1", "rot_2", "rot_3")):
        w, x, y, z = g["rot_0"], g["rot_1"], g["rot_2"], g["rot_3"]
        out["rot_0"], out["rot_1"], out["rot_2"], out["rot_3"] = -z, -y, x, w
    return out
