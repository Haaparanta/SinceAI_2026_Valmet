"""scripts/splat_format.py: scene.splat for the viewer's Splats mode, the .splat layout, 32 bytes per splat."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location("splat_format", ROOT / "scripts" / "splat_format.py")
assert _spec and _spec.loader
fmt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fmt)

# the INRIA SH-0 fields both builds use (stepbuild.splats.SH0_DTYPE, autoscene.splats.SH0_DTYPE)
SH0_DTYPE = np.dtype([(f, "<f4") for f in (
    "x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
    "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3",
)])


def _splats() -> np.ndarray:
    s = np.zeros(3, SH0_DTYPE)
    s["x"], s["y"], s["z"] = [1.5, -2.0, 0.25], [0.0, -1.1, 3.0], [-4.0, 0.5, 2.0]
    s["scale_0"], s["scale_1"], s["scale_2"] = np.log([0.01, 0.2, 1.0]), np.log([0.02, 0.2, 1.0]), np.log([0.03, 0.2, 1.0])
    s["f_dc_0"] = [0.0, 1.0, -10.0]  # 0.5 + C0 * dc: 0.5, ~0.78, clamped to 0
    s["opacity"] = [0.0, 30.0, -30.0]  # sigmoid: 0.5, ~1, ~0
    # (w, x, y, z): identity, 90 deg about y (unnormalised on purpose), and an all-zero quaternion
    s["rot_0"], s["rot_1"], s["rot_2"], s["rot_3"] = [1.0, 2.0, 0.0], [0.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 0.0]
    return s


def test_splat_rows_are_32_bytes_in_the_splat_layout() -> None:
    s = _splats()
    b = fmt.splat_bytes(s)
    assert b.shape == (3, 32) and b.dtype == np.uint8
    xyz = b[:, 0:12].copy().view("<f4").reshape(3, 3)
    np.testing.assert_allclose(xyz, np.stack([s["x"], s["y"], s["z"]], 1))
    scale = b[:, 12:24].copy().view("<f4").reshape(3, 3)
    np.testing.assert_allclose(scale[0], [0.01, 0.02, 0.03], rtol=1e-5)
    assert list(b[:, 24]) == [128, 199, 0]  # red from SH0
    assert list(b[:, 27]) == [128, 255, 0]  # alpha = sigmoid(opacity)
    assert list(b[0, 28:32]) == [255, 128, 128, 128]  # identity, w first
    w = b[1, 28:32].astype(float) - 128.0
    np.testing.assert_allclose(w / 128.0, [np.sqrt(0.5), 0, np.sqrt(0.5), 0], atol=0.01)  # normalised
    assert list(b[2, 28:32]) == [255, 128, 128, 128]  # a zero quaternion becomes identity


def test_bad_scales_do_not_blow_up() -> None:
    s = _splats()
    s["scale_0"][0] = np.nan
    s["scale_1"][0] = 50.0
    scale = fmt.splat_bytes(s)[:, 12:24].copy().view("<f4").reshape(3, 3)
    assert np.isfinite(scale).all() and scale.max() <= np.exp(4.0) + 1e-3


def test_write_splat_writes_the_rows(tmp_path: Path) -> None:
    s = _splats()
    path = tmp_path / "scene.splat"
    fmt.write_splat(path, s)
    assert path.read_bytes() == fmt.splat_bytes(s).tobytes()
    assert not (tmp_path / "scene.splat.tmp").exists()
