"""Step-by-step build helpers (pipeline/stepbuild): image naming, manifest pool, PLY writer, renderer. No PLY needed."""

from datetime import datetime
from pathlib import Path

import numpy as np
from common.ply_io import read_header
from stepbuild import render as R
from stepbuild import state as S
from stepbuild.splats import SH0_DTYPE, SH0_FIELDS, write_sh0_ply


def test_image_name_is_index_then_local_timestamp(tmp_path: Path) -> None:
    when = datetime(2026, 11, 6, 21, 5, 9)
    assert S.image_path(7, when, tmp_path).name == "0007_20261106-210509.png"


def test_next_image_index_continues_after_highest(tmp_path: Path) -> None:
    assert S.next_image_index(tmp_path) == 1
    for name in ("0001_20261106-210000.png", "0012_20261106-210500.png", "notes.png", "0003_x.png"):
        (tmp_path / name).write_bytes(b"")
    assert S.next_image_index(tmp_path) == 13


def test_pool_excludes_removed_and_claimed(tmp_path: Path) -> None:
    m = S.Manifest.new("scan.ply", 20, 10)
    np.save(tmp_path / "rm.npy", np.array([0, 1], dtype=np.uint32))
    np.save(tmp_path / "floor.npy", np.array([5, 6, 7], dtype=np.uint32))
    m.data["removed"].append({"indices": "rm.npy"})
    m.data["parts"].append({"indices": "floor.npy"})
    pool = m.pool_mask(tmp_path)
    assert pool.tolist() == [False, False, True, True, True, False, False, False, True, True]


def test_sh0_ply_round_trip(tmp_path: Path) -> None:
    rows = np.zeros(3, dtype=SH0_DTYPE)
    rows["x"] = [1, 2, 3]
    rows["rot_0"] = 1
    path = tmp_path / "part.ply"
    write_sh0_ply(path, rows, "test")
    n, offset, names = read_header(str(path))
    assert n == 3 and tuple(names) == SH0_FIELDS
    back = np.fromfile(path, dtype=SH0_DTYPE, offset=offset)
    assert back["x"].tolist() == [1, 2, 3]
    write_sh0_ply(path, np.empty(0, dtype=SH0_DTYPE))  # the empty starting state is a valid file
    assert read_header(str(path))[0] == 0


def test_framing_camera_hits_fill() -> None:
    lo, hi = np.array([0.0, -0.9, -3.4]), np.array([1.0, 0.2, -2.9])
    for fill in (0.2, 0.25, 0.3):
        cam = R.framing_camera(lo, hi, np.array([0.0, -0.3, -1.0]), fill=fill)
        assert abs(max(R.screen_span(R.box_corners(lo, hi), cam)) - fill) < 0.01


def test_nearest_point_wins() -> None:
    cam = R.Camera((0.0, 0.0, 5.0), (0.0, 0.0, 0.0), 40.0)
    near = R.Layer(np.array([[0.0, 0.0, 1.0]], dtype=np.float32), R.RED, "near")
    far = R.Layer(np.array([[0.0, 0.0, -1.0]], dtype=np.float32), R.GREY, "far")
    frame = R.render([far, near], cam, 64, 48, edl_strength=0)
    assert tuple(frame.image[24, 32]) == R.RED
    assert frame.counts["near"] > 0 and frame.counts["far"] == 0


def test_blend_composites_front_to_back() -> None:
    cam = R.Camera((0.0, 0.0, 5.0), (0.0, 0.0, 0.0), 40.0)
    red = np.array([[255, 0, 0]], dtype=np.uint8)
    blue = np.array([[0, 0, 255]], dtype=np.uint8)
    one = R.render_blend([R.BlendLayer(np.array([[0.0, 0.0, 0.0]], np.float32), red, 0.8)], cam, 64, 48,
                         background=(0, 0, 0))
    assert tuple(one.image[24, 32]) == (204, 0, 0)                       # 0.8 x 255
    two = R.render_blend([R.BlendLayer(np.array([[0.0, 0.0, -1.0]], np.float32), blue, 1.0),
                          R.BlendLayer(np.array([[0.0, 0.0, 1.0]], np.float32), red, 0.5)], cam, 64, 48,
                         background=(0, 0, 0))
    got = two.image[24, 32].astype(int)                                   # half red in front of opaque blue
    assert np.abs(got - np.array([128, 0, 128])).max() <= 1              # (alpha is capped at 0.999)


def test_gaussian_splat_is_an_ellipse_with_its_colour_and_opacity() -> None:
    from stepbuild.splats import SH0_DTYPE

    g = np.zeros(1, dtype=SH0_DTYPE)
    g["rot_0"] = 1.0
    g["scale_0"], g["scale_1"], g["scale_2"] = np.log(0.2), np.log(0.05), np.log(0.05)   # long along x
    g["opacity"] = 10.0                                                                   # alpha ~1
    g["f_dc_0"] = (1.0 - 0.5) / 0.28209479                                                # red 255
    g["f_dc_1"] = g["f_dc_2"] = (0.0 - 0.5) / 0.28209479
    cam = R.Camera((0.0, 0.0, 5.0), (0.0, 0.0, 0.0), 40.0)
    f = R.render_gaussians(g, cam, 200, 150, max_radius_px=40, background=(0, 0, 0))
    centre = f.image[75, 100]
    assert centre[0] > 240 and centre[1] < 10                                             # opaque red centre
    row, col = f.image[75, :, 0], f.image[:, 100, 0]
    assert (row > 128).sum() > 2.5 * (col > 128).sum()                                    # wider than tall


def test_splat_scale_keeps_the_full_room_within_budget() -> None:
    assert R.splat_scale(100_000, 18) == 2
    assert R.splat_scale(1_617_777, 18) == 3        # the whole room: 1/3 (~17 s)
    assert R.splat_scale(1_617_777, 8) >= 5
