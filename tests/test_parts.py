"""Part detectors (pipeline/stepbuild/parts.py) on a synthetic room; no PLY needed."""

import numpy as np
from stepbuild.parts import floor

from tests.test_cleaning import synthetic_room


def test_floor_takes_the_slab_and_nothing_above() -> None:
    xyz = synthetic_room(4)
    xyz = xyz[xyz[:, 1] > -0.95]                                   # as after step 2a
    prop = floor(xyz, xyz.min(0), xyz.max(0))
    taken = xyz[prop.take]
    assert prop.name == "floor" and prop.kind == "structure"
    assert (taken[:, 1] <= prop.info["floor_y"] + 0.03 + 1e-6).all()
    on_slab = np.abs(xyz[:, 1] + 0.91) < 0.025
    assert prop.take[on_slab].mean() > 0.99                        # the slab is taken
    assert not prop.take[xyz[:, 1] > -0.85].any()                  # nothing standing on it


def test_ceiling_is_the_flat_top_layer_not_pipes_running_under_it() -> None:
    from stepbuild.parts import ceiling
    from stepbuild.splats import SH0_DTYPE

    rng = np.random.default_rng(7)
    n_floor, n_room, n_band, n_high, n_ceil, n_lamp = 20000, 30000, 40000, 4000, 6000, 800
    y = np.r_[rng.normal(-1.07, 0.01, n_floor), rng.uniform(-1.0, 0.6, n_room),
              rng.normal(0.88, 0.05, n_band),                  # the dense pipe band
              rng.uniform(1.15, 1.25, n_high),                 # pipes running just under the ceiling
              rng.normal(1.30, 0.01, n_ceil),                  # the flat ceiling
              rng.normal(1.27, 0.02, n_lamp)]                  # white lamps hanging a bit lower
    x = rng.uniform(-3, 3, len(y))
    x[n_floor + n_room + n_band:n_floor + n_room + n_band + n_high] = rng.uniform(-0.1, 0.1, n_high)  # one pipe run
    xyz = np.c_[x, y, rng.uniform(-3.4, -0.8, len(y))].astype(np.float32)
    pool = np.zeros(len(y), dtype=SH0_DTYPE)
    pool["f_dc_0"][-n_lamp:] = pool["f_dc_1"][-n_lamp:] = pool["f_dc_2"][-n_lamp:] = 3.0  # saturated white
    prop = ceiling(xyz, xyz.min(0), xyz.max(0), pool=pool)
    b0 = n_floor + n_room + n_band
    assert abs(prop.info["ceiling_y"] - 1.30) < 0.03
    assert prop.take[b0 + n_high:b0 + n_high + n_ceil].mean() > 0.9     # the flat ceiling is taken
    assert prop.take[b0:b0 + n_high].mean() < 0.1                       # pipes under it stay
    assert not prop.take[-n_lamp:].any()                                # lamps are left for their own part
    assert prop.take[:b0].sum() == 0
