"""Cleaning filters and plane finder (pipeline/stepbuild) on synthetic rooms; no PLY needed."""

import numpy as np
from stepbuild.cleaning import below_floor
from stepbuild.geometry import horizontal_plane


def synthetic_room(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    floor = np.c_[rng.uniform(-4, 4, 6000), rng.normal(-0.91, 0.015, 6000), rng.uniform(-3.4, -0.8, 6000)]
    ceiling = np.c_[rng.uniform(-4, 4, 4000), rng.normal(1.07, 0.015, 4000), rng.uniform(-3.4, -0.8, 4000)]
    stuff = np.c_[rng.uniform(-4, 4, 3000), rng.uniform(-0.85, 1.0, 3000), rng.uniform(-3.4, -0.8, 3000)]
    mirror = np.c_[rng.uniform(-4, 4, 800), rng.uniform(-1.6, -1.0, 800), rng.uniform(-3.4, -0.8, 800)]
    return np.vstack([floor, ceiling, stuff, mirror]).astype(np.float32)


def test_floor_and_ceiling_planes() -> None:
    xyz = synthetic_room()
    floor = horizontal_plane(xyz[:, 1], lower=True)
    ceiling = horizontal_plane(xyz[:, 1], lower=False)
    assert abs(floor.y + 0.91) < 0.005 and floor.rms < 0.02
    assert abs(ceiling.y - 1.07) < 0.005


def test_below_floor_removes_only_the_mirror() -> None:
    xyz = synthetic_room()
    prop = below_floor(xyz, xyz.min(0), xyz.max(0), margin=0.04)
    removed = xyz[prop.remove]
    # the 800 mirror points + the floor-noise tail beyond 4 cm (sigma 1.5 cm: ~0.4-0.6 % of 6000 floor points)
    assert 800 <= len(removed) < 870
    assert (removed[:, 1] < -0.94).all()
    assert prop.info["cut_y"] == round(prop.info["floor_y"] - 0.04, 4)
