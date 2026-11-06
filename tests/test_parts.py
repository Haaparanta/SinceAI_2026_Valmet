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
