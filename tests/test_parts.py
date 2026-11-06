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


def test_ceiling_is_above_the_pipe_band_and_leaves_lamps_out() -> None:
    from stepbuild.parts import ceiling
    from stepbuild.splats import SH0_DTYPE

    rng = np.random.default_rng(7)
    n_floor, n_room, n_pipes, n_ceil, n_lamp = 20000, 30000, 40000, 6000, 800
    y = np.r_[rng.normal(-1.07, 0.01, n_floor), rng.uniform(-1.0, 0.6, n_room), rng.normal(0.88, 0.05, n_pipes),
              rng.normal(1.27, 0.05, n_ceil), rng.normal(1.33, 0.03, n_lamp)]
    xyz = np.c_[rng.uniform(-3, 3, len(y)), y, rng.uniform(-3.4, -0.8, len(y))].astype(np.float32)
    pool = np.zeros(len(y), dtype=SH0_DTYPE)
    pool["f_dc_0"] = pool["f_dc_1"] = pool["f_dc_2"] = 0.0                      # mid grey
    pool["f_dc_0"][-n_lamp:] = pool["f_dc_1"][-n_lamp:] = pool["f_dc_2"][-n_lamp:] = 3.0  # saturated white
    prop = ceiling(xyz, xyz.min(0), xyz.max(0), pool=pool)
    assert 1.0 < prop.info["split_y"] < 1.2
    assert prop.take[-n_lamp - n_ceil:-n_lamp].mean() > 0.95                    # the ceiling layer is taken
    assert not prop.take[-n_lamp:].any()                                         # lamps are left for their own part
    assert prop.take[:n_floor + n_room].sum() == 0                               # nothing from the room
    assert prop.take[n_floor + n_room:n_floor + n_room + n_pipes].mean() < 0.02  # (almost) nothing from the pipes
