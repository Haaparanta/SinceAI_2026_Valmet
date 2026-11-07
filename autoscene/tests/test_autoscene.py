"""Unit tests on synthetic data: no PLY, no model, each under a second."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from autoscene import render as R
from autoscene.detect2d import Detection, mask_to_splats
from autoscene.merge import merge_masks
from autoscene.rebuild import obb_yup, slug
from autoscene.splats import SH0_DTYPE


def _splats(xyz: np.ndarray, rgb=(0.8, 0.2, 0.2), scale=-4.0, opacity=4.0) -> np.ndarray:
    s = np.zeros(len(xyz), dtype=SH0_DTYPE)
    s["x"], s["y"], s["z"] = xyz.T
    for k, name in enumerate(("f_dc_0", "f_dc_1", "f_dc_2")):
        s[name] = (rgb[k] - 0.5) / 0.28209479
    s["opacity"] = opacity
    s["scale_0"] = s["scale_1"] = s["scale_2"] = scale
    s["rot_0"] = 1.0
    return s


def test_obb_yup_recovers_a_yawed_box():
    rng = np.random.default_rng(0)
    local = rng.uniform(-1, 1, (4000, 3)) * np.array([1.0, 0.25, 0.1])
    yaw = np.radians(30)
    Rm = np.array([[np.cos(yaw), 0, -np.sin(yaw)], [0, 1, 0], [np.sin(yaw), 0, np.cos(yaw)]])
    p = local @ Rm.T + np.array([2.0, -1.0, 0.5])
    box = obb_yup(p)
    assert abs(abs(box["yaw_deg"]) % 180 - 30) < 2 or abs(abs(box["yaw_deg"]) % 180 - 150) < 2
    ext = sorted(box["extent"], reverse=True)
    assert abs(ext[0] - 1.92) < 0.08 and abs(ext[1] - 0.48) < 0.04 and abs(ext[2] - 0.19) < 0.03
    assert np.allclose(box["center"], [2.0, -1.0, 0.5], atol=0.05)
    assert len(box["corners"]) == 8


def test_mask_to_splats_keeps_the_front_layer_only():
    ids = np.full((10, 10), -1, np.int32)
    depth = np.full((10, 10), np.inf, np.float32)
    ids[2:8, 2:8] = np.arange(36).reshape(6, 6)
    depth[2:8, 2:8] = 2.0
    ids[4, 4], depth[4, 4] = 99, 9.0                      # background seen through a gap
    mask = np.zeros((10, 10), bool)
    mask[1:9, 1:9] = True
    got = mask_to_splats(mask, ids, depth)
    assert 99 not in got and len(got) == 35
    exclude = np.zeros(100, bool)
    exclude[:5] = True
    got = mask_to_splats(mask, ids, depth, exclude)
    assert got.min() == 5


def test_merge_masks_does_not_chain_two_objects_seen_apart():
    """Masks: A1 (view 0) and A2 (view 1) = object A, B1 (view 0), B2 (view 1) = object B, and C (view 2) covers A and
    B together. Union-find would merge everything through C; consensus keeps A and B apart because views 0 and 1 see
    both and put them in different masks."""
    n = 200
    a, b = np.arange(0, 100), np.arange(100, 200)
    masks = [a, b, a, b, np.arange(0, 200)]
    view = np.array([0, 0, 1, 1, 2])
    rows = np.concatenate([np.full(len(m), k) for k, m in enumerate(masks)])
    cols = np.concatenate(masks)
    M = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(5, n))
    vis = sparse.csr_matrix(np.ones((3, n), np.float32))
    comp = merge_masks(M, view, vis)
    assert comp[0] == comp[2] and comp[1] == comp[3]
    assert comp[0] != comp[1]
    assert comp[4] in (comp[0], comp[1]) or comp[4] not in (comp[0], comp[1])   # C joins one side or stays alone


def test_rasterizer_draws_a_red_blob_with_ids():
    from autoscene import rasterize as RZ
    xyz = np.array([[0.0, 0.0, 2.0], [0.05, 0.0, 2.0]])
    s = _splats(xyz, scale=-3.0)
    cam = R.Camera((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 50.0)
    img, ids, depth = RZ.render(s, cam, 64, 48, ids=np.array([10, 20]))
    assert img[24, 32, 0] > 150 and img[24, 32, 1] < 100
    assert set(np.unique(ids)) <= {-1, 10, 20} and (ids >= 0).any()
    assert np.isfinite(depth[ids >= 0]).all() and abs(float(depth[ids >= 0].min()) - 2.0) < 0.01
    faint = np.full(2, 0.05, np.float32)
    img2, _, _ = RZ.render(s, cam, 64, 48, alpha_scale=faint)
    assert img2[24, 32, 0] < img[24, 32, 0]


def test_slug_and_detection_roundtrip(tmp_path):
    from autoscene.detect2d import load_detections, save_detections
    assert slug("Washing Machine!") == "washing_machine"
    dets = [Detection(0, "pipe", 0.5, (1, 2, 3, 4), None, np.array([5, 6, 7], np.int32), 12),
            Detection(1, "valve", 0.25, (0, 0, 9, 9), None, np.array([8], np.int32), 3)]
    save_detections(dets, tmp_path / "d.npz")
    back = load_detections(tmp_path / "d.npz")
    assert [d.label for d in back] == ["pipe", "valve"]
    assert back[0].box == (1, 2, 3, 4) and back[1].splat_ids.tolist() == [8] and back[0].n_pixels == 12
