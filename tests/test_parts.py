"""Part detectors (pipeline/stepbuild/parts.py) on a synthetic room; no PLY needed."""

import numpy as np
from stepbuild.parts import floor
from stepbuild.parts import floor as floor_fn

from tests.test_cleaning import synthetic_room


def test_floor_takes_the_slab_and_nothing_above() -> None:
    xyz = synthetic_room(4)
    xyz = xyz[xyz[:, 1] > -0.95]                                   # as after step 2a
    prop = floor(xyz, xyz.min(0), xyz.max(0))
    taken = xyz[prop.take]
    assert prop.name == "floor" and prop.kind == "structure"
    a_, b_, c_ = prop.info["plane"]
    assert (taken[:, 1] <= a_ * taken[:, 0] + b_ * taken[:, 2] + c_ + 0.025 + 1e-6).all()
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


def test_lamp_takes_the_largest_white_cluster_up_high() -> None:
    from stepbuild.parts import lamp
    from stepbuild.splats import SH0_DTYPE

    rng = np.random.default_rng(8)
    big = np.c_[rng.uniform(-2.2, -0.8, 1500), rng.normal(1.35, 0.03, 1500), rng.normal(-2.45, 0.03, 1500)]
    small = np.c_[rng.uniform(0.4, 1.1, 500), rng.normal(1.35, 0.03, 500), rng.normal(-2.45, 0.03, 500)]
    low_white = np.c_[rng.uniform(-2, 2, 800), rng.normal(0.85, 0.03, 800), rng.uniform(-3, -1, 800)]  # white pipes
    grey = np.c_[rng.uniform(-3, 3, 3000), rng.uniform(-1, 1.5, 3000), rng.uniform(-3.4, -0.8, 3000)]
    xyz = np.vstack([big, small, low_white, grey]).astype(np.float32)
    pool = np.zeros(len(xyz), dtype=SH0_DTYPE)
    n_white = len(big) + len(small) + len(low_white)
    pool["f_dc_0"][:n_white] = pool["f_dc_1"][:n_white] = pool["f_dc_2"][:n_white] = 3.0
    prop = lamp(xyz, xyz.min(0), xyz.max(0), pool=pool, number=1)
    assert prop.name == "lamp_1" and prop.kind == "equipment"
    assert prop.take[:len(big)].mean() > 0.95                  # the big tube
    assert not prop.take[len(big):].any()                      # not the smaller tube, white pipes or grey points


def test_floor_follows_a_tilted_plane() -> None:
    rng = np.random.default_rng(11)
    n = 40000
    x, z = rng.uniform(-4, 4.8, n), rng.uniform(-3.6, 3.4, n)
    floor = np.c_[x, -0.0025 * x - 0.0049 * z - 1.174 + rng.normal(0, 0.01, n), z]
    m = 30000
    above = np.c_[rng.uniform(-4, 4.8, m), rng.uniform(-1.0, 1.0, m), rng.uniform(-3.6, 3.4, m)]
    low_box = np.c_[rng.uniform(3, 4, 2000), rng.uniform(-1.16, -1.15, 2000), rng.uniform(2.5, 3.3, 2000)]  # 4+ cm up
    xyz = np.vstack([floor, above, low_box]).astype(np.float32)
    prop = floor_fn(xyz, xyz.min(0), xyz.max(0))
    assert abs(prop.info["plane"][2] + 1.174) < 0.005 and prop.info["tilt_deg"] > 0.2
    assert prop.take[:n].mean() > 0.97                         # the whole tilted floor
    assert prop.take[n:n + m].sum() == 0                       # nothing standing higher
    assert prop.take[n + m:].sum() == 0                         # a box 4-5 cm above the low corner stays
    # (a flat cut at the mean floor height + 3 cm would take it: the low corner is 2.3 cm below the mean)


def test_wall_takes_the_wall_layer_not_equipment_along_it() -> None:
    from stepbuild.parts import wall

    rng = np.random.default_rng(12)
    room = np.c_[rng.uniform(-4, 4.8, 60000), rng.uniform(-1.1, 1.2, 60000), rng.uniform(-3.4, 3.4, 60000)]
    skin = np.c_[rng.uniform(-4, 4.8, 3000), rng.uniform(-1.1, 1.2, 3000), rng.normal(-3.75, 0.01, 3000)]
    layer = np.c_[rng.uniform(-4, 4.8, 20000), rng.uniform(-1.1, 1.2, 20000), rng.normal(-3.68, 0.012, 20000)]
    pipes = np.c_[rng.uniform(-4, 4.8, 15000), rng.uniform(-1.1, 1.2, 15000), rng.normal(-3.44, 0.02, 15000)]
    xyz = np.vstack([room, skin, layer, pipes]).astype(np.float32)
    prop = wall(xyz, xyz.min(0), xyz.max(0), side="back")
    a, b = len(room), len(room) + len(skin) + len(layer)
    assert prop.name == "wall_back" and abs(prop.info["main_layer_median"] + 3.68) < 0.02
    assert prop.take[a:b].mean() > 0.97                          # outer skin + main layer
    assert prop.take[b:].sum() == 0                              # pipes 24 cm in front stay
    assert prop.take[:a].mean() < 0.01                           # the room stays


def test_equipment_grows_the_object_at_the_seed_only() -> None:
    from stepbuild.parts import equipment
    from stepbuild.splats import SH0_DTYPE

    rng = np.random.default_rng(13)
    pump = np.c_[rng.uniform(3.1, 3.3, 8000), rng.uniform(-1.0, -0.3, 8000), rng.uniform(-1.46, -1.26, 8000)]
    other = np.c_[rng.uniform(2.1, 2.3, 6000), rng.uniform(-1.0, -0.3, 6000), rng.uniform(-1.46, -1.26, 6000)]  # 1 u away
    xyz = np.vstack([pump, other]).astype(np.float32)
    pool = np.zeros(len(xyz), dtype=SH0_DTYPE)
    pool["opacity"] = 2.0
    prop = equipment(xyz, xyz.min(0), xyz.max(0), pool=pool, x=3.2, y=-0.6, z=-1.36, radius=0.8, label="Pump",
                     cls="PROCESS_PUMP", number=1)
    assert prop.name == "process_pump_1" and prop.label == "Pump 1"
    assert prop.take[:len(pump)].mean() > 0.95
    assert not prop.take[len(pump):].any()
