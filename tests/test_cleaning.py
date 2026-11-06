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


def test_back_wall_profile_follows_recess_and_ignores_equipment() -> None:
    from stepbuild.geometry import back_wall_profile

    rng = np.random.default_rng(1)
    x = rng.uniform(-4, 4, 40000)
    wall_z = np.where((x > -1.5) & (x < 0.0), -3.47, -3.41)                  # recess between x -1.5 and 0
    z = wall_z + rng.normal(0, 0.01, len(x))
    ex = rng.uniform(2.0, 3.0, 30000)                                         # dense equipment in front, x 2..3
    ez = rng.normal(-3.18, 0.01, len(ex))
    fx, fz = rng.uniform(-4, 4, 3000), rng.uniform(-5.0, -3.6, 3000)          # diffuse floaters behind
    rx, rz = rng.uniform(-4, 4, 60000), rng.uniform(-3.4, -0.75, 60000)       # the room in front (floor, stuff)
    prof = back_wall_profile(np.r_[x, ex, fx, rx], np.r_[z, ez, fz, rz])
    assert abs(prof.global_depth + 3.41) < 0.01
    assert abs(prof.at(np.array([-0.75]))[0] + 3.47) < 0.01                   # recess found
    assert abs(prof.at(np.array([2.5]))[0] + 3.41) < 0.02                     # equipment strip keeps the wall
    assert (prof.depth <= prof.global_depth + 0.03 + 1e-9).all()              # never far in front of the wall


def test_floating_fog_keeps_faint_splats_on_surfaces() -> None:
    from stepbuild.cleaning import floating_fog
    from stepbuild.splats import SH0_DTYPE

    rng = np.random.default_rng(2)
    n_solid, n_faint_surface, n_faint_air = 4000, 1000, 300
    xyz = np.vstack([
        np.c_[rng.uniform(0, 2, n_solid), np.full(n_solid, -0.91), rng.uniform(-2, 0, n_solid)],
        np.c_[rng.uniform(0, 2, n_faint_surface), np.full(n_faint_surface, -0.90), rng.uniform(-2, 0, n_faint_surface)],
        np.c_[rng.uniform(0, 2, n_faint_air), rng.uniform(-0.5, 0.5, n_faint_air), rng.uniform(-2, 0, n_faint_air)],
    ]).astype(np.float32)
    pool = np.zeros(len(xyz), dtype=SH0_DTYPE)
    pool["opacity"] = np.r_[np.full(n_solid, 2.0), np.full(n_faint_surface + n_faint_air, -4.0)]  # 0.88 vs 0.018
    prop = floating_fog(xyz, xyz.min(0), xyz.max(0), pool=pool)
    assert prop.remove[:n_solid + n_faint_surface].sum() == 0
    assert prop.remove[n_solid + n_faint_surface:].all()
