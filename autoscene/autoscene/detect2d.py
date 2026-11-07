"""Stage 5: 2D objects in every rendered view with YOLOE-26 (Ultralytics), text-prompted.

Measured 2026-11-07 on the M1 (8 GB): yoloe-26s-seg, imgsz 1024, MPS ~0.1-0.3 s per picture after warm-up, CPU
~2 s. The text encoder (MobileCLIP2-B, 242 MB) runs once at set_classes. Prompt-free mode (4,585 names) was tried
on the same picture and returned "tattoo artist" and "pantyhose" for pipes: it is off by default.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from autoscene import ROOT

log = logging.getLogger("autoscene.detect2d")

WEIGHTS = ROOT / "weights"

# The vocabulary of an industrial equipment / boiler room, phrased as everyday category names (the YOLOE docs say
# appearance words work, relational words do not). Order does not matter; each label carries its own score.
VOCABULARY = [
    "pipe", "insulated pipe", "valve", "pump", "electric motor", "tank", "boiler", "pressure vessel",
    "control cabinet", "electrical panel", "junction box", "ladder", "pallet jack", "barrel", "bucket",
    "fire extinguisher", "lamp", "door", "cart", "pressure gauge", "thermometer", "hose", "fan", "duct",
    "cable", "cable tray", "window", "sign", "shelf", "cardboard box", "chair", "table", "trash can",
    "radiator", "heat exchanger", "compressor", "water heater", "meter", "flange", "bottle", "poster",
    "light switch", "cabinet", "bag", "crate", "roll cage", "tool box", "wheel", "railing", "beam", "column",
    "manifold", "filter", "expansion tank", "boiler burner", "control panel", "pipe elbow", "bracket",
    "washing machine", "office chair", "step ladder", "trolley", "gas cylinder", "paint can", "bin", "exit sign",
    "hose reel", "workbench", "wire cage", "water bottle", "canister", "pressure regulator", "circulation pump",
    "boiler unit", "storage rack", "wooden pallet", "clipboard", "first aid kit", "vacuum cleaner", "broom",
]


@dataclass
class Detection:
    view: int                   # index into the views list
    label: str
    score: float
    box: tuple[int, int, int, int]          # x0, y0, x1, y1 pixels
    mask: np.ndarray | None = None          # bool[H, W] at the view's resolution (not saved)
    splat_ids: np.ndarray | None = None     # int32: the splats under the mask, depth-gated (lift.mask_to_splats)
    n_pixels: int = 0


def mask_to_splats(mask: np.ndarray, ids: np.ndarray, depth: np.ndarray, exclude: np.ndarray | None = None,
                   slack: float = 0.15) -> np.ndarray:
    """Splat indices under a mask, keeping only the dominant depth layer: pixels deeper than
    p75 + 1.5 IQR + slack are background seen through gaps. `exclude` is a bool over all splats (floor/ceiling)."""
    sel = mask & (ids >= 0)
    if exclude is not None:
        sel &= ~exclude[np.where(ids >= 0, ids, 0)]
    d = depth[sel]
    if len(d) == 0:
        return np.zeros(0, np.int32)
    q1, q3 = np.percentile(d, [25, 75])
    far = q3 + 1.5 * (q3 - q1) + slack
    return np.unique(ids[sel][d <= far]).astype(np.int32)


@dataclass
class Detector:
    weights: str = "yoloe-26s-seg.pt"
    vocabulary: list[str] = field(default_factory=lambda: list(VOCABULARY))
    device: str = "mps"
    imgsz: int = 1024
    conf: float = 0.12
    model: object = None

    def load(self) -> Detector:
        import torch
        from ultralytics import YOLOE
        if self.device == "mps" and not torch.backends.mps.is_available():
            self.device = "cpu"
        path = WEIGHTS / self.weights
        WEIGHTS.mkdir(exist_ok=True)
        cwd = Path.cwd()
        try:
            import os
            os.chdir(WEIGHTS)                        # ultralytics downloads into the cwd
            self.model = YOLOE(str(path) if path.exists() else self.weights)
            self.model.set_classes(self.vocabulary)
        finally:
            os.chdir(cwd)
        log.info("YOLOE %s loaded on %s with %d prompts", self.weights, self.device, len(self.vocabulary))
        return self

    def detect(self, image: np.ndarray, view: int, max_area: float = 0.45) -> list[Detection]:
        """Detections on one RGB picture. Masks covering more than `max_area` of the picture are dropped (floor,
        wall, the whole room). The caller turns masks into splat ids (mask_to_splats) before saving."""
        res = self.model.predict(image, conf=self.conf, verbose=False, device=self.device, imgsz=self.imgsz,
                                 retina_masks=True)[0]
        out: list[Detection] = []
        if res.masks is None or len(res.boxes) == 0:
            return out
        masks = res.masks.data.cpu().numpy() > 0.5
        h, w = image.shape[:2]
        for k, b in enumerate(res.boxes):
            m = masks[k]
            if m.shape != (h, w):
                from PIL import Image
                m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 127
            if m.mean() > max_area or m.sum() < 40:
                continue
            x0, y0, x1, y1 = (int(v) for v in b.xyxy[0].tolist())
            out.append(Detection(view, self.vocabulary[int(b.cls)], float(b.conf), (x0, y0, x1, y1), m,
                                 n_pixels=int(m.sum())))
        return out


def save_detections(dets: list[Detection], path: Path) -> None:
    """detections.npz: a table (view, label index, score, box, n_pixels, n_splats) + the splat ids concatenated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = sorted({d.label for d in dets})
    table = np.array([(d.view, labels.index(d.label), d.score, *d.box, d.n_pixels, len(d.splat_ids)) for d in dets],
                     dtype=np.float64).reshape(-1, 9)
    ids = np.concatenate([d.splat_ids for d in dets]) if dets else np.zeros(0, np.int32)
    np.savez_compressed(path, table=table, ids=ids.astype(np.int32), labels=np.array(labels))


def load_detections(path: Path) -> list[Detection]:
    z = np.load(path)
    labels, ids = list(z["labels"]), z["ids"]
    out, pos = [], 0
    for row in z["table"]:
        n = int(row[8])
        out.append(Detection(int(row[0]), str(labels[int(row[1])]), float(row[2]), tuple(int(v) for v in row[3:7]),
                             None, ids[pos:pos + n], int(row[7])))
        pos += n
    return out
