"""World orientation (pipeline/common/orientation.py): 180 deg about z for positions and quaternions."""

import numpy as np
from common.orientation import to_world
from stepbuild.splats import SH0_DTYPE


def quat_matrix(w: float, x: float, y: float, z: float) -> np.ndarray:
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def test_positions_and_rotations_turn_180_about_z() -> None:
    rng = np.random.default_rng(5)
    g = np.zeros(50, dtype=SH0_DTYPE)
    for f in ("x", "y", "z", "scale_0", "f_dc_0"):
        g[f] = rng.normal(size=50)
    q = rng.normal(size=(50, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    g["rot_0"], g["rot_1"], g["rot_2"], g["rot_3"] = q.T
    w = to_world(g)
    rz = np.diag([-1.0, -1.0, 1.0])
    assert np.allclose(np.c_[w["x"], w["y"], w["z"]], np.c_[g["x"], g["y"], g["z"]] @ rz.T)
    for i in range(50):
        before = quat_matrix(*(float(g[f][i]) for f in ("rot_0", "rot_1", "rot_2", "rot_3")))
        after = quat_matrix(*(float(w[f][i]) for f in ("rot_0", "rot_1", "rot_2", "rot_3")))
        assert np.allclose(after, rz @ before, atol=1e-5)
    assert np.array_equal(w["scale_0"], g["scale_0"]) and np.array_equal(w["f_dc_0"], g["f_dc_0"])
    assert np.linalg.det(rz) == 1.0                    # a rotation, not a mirror: text and handedness stay right
