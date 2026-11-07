"""Stage 7b: a second look at every object with the detector, on its own close-up.

The first pass saw objects in crowded room views. Here each object is rendered alone in full colour with the room
dimmed (the same picture the review images use), YOLOE runs on that picture with the full vocabulary, and the
detection whose box best covers the object's own screen box gives the label. A geometry cluster ("unidentified
object", "pipe fitting") takes the detector's word when the match is good; a detector object keeps its label unless
the close-up disagrees with a clearly better score. Every decision is recorded in the instance's info.
"""

from __future__ import annotations

import logging

import numpy as np

from autoscene import rasterize as RZ
from autoscene import render as R
from autoscene.lift import Instance
from autoscene.scene import Scene
from autoscene.views import frustum_cull

log = logging.getLogger("autoscene.relabel")

W, H = 1024, 640
GENERIC = {"unidentified object", "small object", "pipe fitting", "pipe network", "column", "pipe network remainder"}


def _closeup(sc: Scene, rows: np.ndarray, kept: np.ndarray) -> tuple[np.ndarray, R.Camera]:
    from autoscene.pictures import closeup_camera
    p = sc.xyz[rows]
    cam = closeup_camera(sc, p, fill=0.45)
    cam = R.Camera(cam.position, cam.target, cam.fov_deg)
    j = kept[frustum_cull(sc.xyz[kept], cam, W, H)]
    alpha = np.full(sc.n, 0.10, np.float32)
    alpha[rows] = 1.0
    colour = np.full(sc.n, 0.40, np.float32)
    colour[rows] = 1.0
    img, _, _ = RZ.render(sc.splats[j], cam, W, H, ids=j, alpha_scale=alpha, color_scale=colour)
    return img, cam


def _screen_box(p: np.ndarray, cam: R.Camera) -> tuple[int, int, int, int]:
    return R.project_rect(p[np.random.default_rng(0).choice(len(p), min(len(p), 4000), replace=False)], cam, W, H)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


PIPE_FAMILY = {"pipe", "insulated pipe", "manifold", "valve", "cable tray", "duct", "hose", "pipe elbow", "flange"}
PIPE_CLUSTERS = {"pipe", "vertical pipe"}


def check_closeups(sc: Scene, instances: list[Instance]) -> list[Instance]:
    """Run the detector on every object's own close-up and record the best-covering detection in
    info["closeup_check"] ({label, score, iou} or {label: None}). Decides nothing."""
    from autoscene.detect2d import Detector
    det = Detector(conf=0.15).load()
    kept = sc.kept_idx()
    for k, ins in enumerate(instances):
        img, cam = _closeup(sc, ins.splats, kept)
        own = _screen_box(sc.xyz[ins.splats], cam)
        found = det.detect(img, k, max_area=0.9)
        best, best_q = None, 0.0
        for d in found:
            iou = _iou(own, d.box)
            if iou >= 0.45 and iou * d.score > best_q:
                best, best_q = d, iou * d.score
        ins.info["closeup_check"] = ({"label": best.label, "score": round(best.score, 3), "iou": round(_iou(own, best.box), 3)}
                                     if best else {"label": None})
        if k % 25 == 0:
            log.info("close-up check %d/%d", k + 1, len(instances))
    return instances


def apply_policy(instances: list[Instance], min_score: float = 0.25, pipe_min_score: float = 0.3,
                 override_min: float = 0.6, override_margin: float = 0.3) -> list[Instance]:
    """Turn the close-up checks into labels (idempotent: starts from label_before when a check was applied before).
    A generic geometry label takes the detector's word at `min_score`; a pipe run only takes a pipe-family word;
    a detector label is overridden only by a clearly better score (>= override_min and >= confidence + margin)."""
    named = changed = 0
    for ins in instances:
        if "label_before" in ins.info:
            ins.label = ins.info.pop("label_before")
            ins.info.pop("label_source", None)
        chk = ins.info.get("closeup_check") or {}
        label, score = chk.get("label"), float(chk.get("score") or 0.0)
        if not label or label == ins.label:
            continue
        if ins.source == "cluster":
            if ins.label in PIPE_CLUSTERS:
                ok = label in PIPE_FAMILY and score >= pipe_min_score
            else:
                ok = ins.label in GENERIC and score >= min_score
            if ok:
                ins.info["label_before"] = ins.label
                ins.label = label
                ins.confidence = round(min(0.9, 0.5 * score + 0.2), 3)
                ins.scores = {label: round(score, 3)}
                ins.info["label_source"] = "closeup"
                named += 1
        elif score >= override_min and score >= ins.confidence + override_margin:
            ins.info["label_before"] = ins.label
            ins.label = label
            ins.scores[label] = ins.scores.get(label, 0.0) + score
            ins.info["label_source"] = "closeup-override"
            changed += 1
    log.info("close-up policy: %d clusters named, %d detector labels changed", named, changed)
    return instances


def relabel(sc: Scene, instances: list[Instance]) -> list[Instance]:
    return apply_policy(check_closeups(sc, instances))
