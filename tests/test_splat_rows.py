"""Real-row prefix detection (pipeline/common/splat_rows.py) on synthetic splat rows; no PLY needed."""

import numpy as np
from common.splat_rows import real_row_count, row_is_plausible

NAMES = ["x", "y", "z", "scale_0", "scale_1", "scale_2", "rot_1", "rot_2", "rot_3", "rot_0",
         "f_dc_0", "f_dc_1", "f_dc_2", "opacity"] + [f"f_rest_{i}" for i in range(3)]


def make_rows(n_real: int, n_garbage: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    g = np.zeros(n_real + n_garbage, dtype=[(n, "<f4") for n in NAMES])
    for f in ("x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "f_rest_0", "f_rest_1", "f_rest_2"):
        g[f][:n_real] = rng.normal(0, 1, n_real)
    for f in ("scale_0", "scale_1", "scale_2"):
        g[f][:n_real] = rng.uniform(-6, -1, n_real)
    q = rng.normal(0, 1, (n_real, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    for i, f in enumerate(("rot_0", "rot_1", "rot_2", "rot_3")):
        g[f][:n_real] = q[:, i]
    tail = g[n_real:].view(np.uint32).reshape(n_garbage, len(NAMES))
    tail[:] = rng.integers(0, 2**32, tail.shape, dtype=np.uint32)  # random bit patterns, like the boiler-room tail
    return g


def test_prefix_found() -> None:
    g = make_rows(1000, 3000)
    assert real_row_count(g) == (1000, 0)


def test_clean_file_unchanged() -> None:
    g = make_rows(500, 0)
    assert real_row_count(g) == (500, 0)


def test_half_written_row_is_rejected() -> None:
    g = make_rows(10, 5)
    g[9]["f_rest_1"] = np.float32(1.4e28)  # sane geometry, garbage SH: the boiler-room row 502,482
    assert not row_is_plausible(g)[9]
    assert real_row_count(g)[0] == 9


def test_nan_and_non_unit_quaternion_rejected() -> None:
    g = make_rows(4, 0)
    g[1]["opacity"] = np.nan
    g[2]["rot_0"] = 2.0
    assert row_is_plausible(g).tolist() == [True, False, False, True]
