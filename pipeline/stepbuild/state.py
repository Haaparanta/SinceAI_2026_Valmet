"""Build state: build/manifest.json (every step, decision and image), build/parts/*.idx.npy, build/current.ply.

Index space = rows of the source PLY (see splats.py). A row is at most one of: removed by a cleaning step, claimed by
an accepted part, or still in the pool. Images go to images/<index>_<YYYYMMDD-HHMMSS>.png (local time); the index
continues from the highest one already in images/, so parallel worktrees stay apart by their timestamps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
IMAGES = ROOT / "images"
MANIFEST = BUILD / "manifest.json"
CURRENT_PLY = BUILD / "current.ply"
PARTS = BUILD / "parts"
REMOVED = BUILD / "removed"
PENDING = BUILD / "pending.json"          # the one proposal waiting for a human decision
PENDING_IDX = BUILD / "pending.idx.npy"
IMAGE_RE = re.compile(r"^(\d{4,})_(\d{8}-\d{6})(?:_[\w-]+)?\.png$")


def now_local() -> datetime:
    return datetime.now().astimezone()


def next_image_index(images: Path = IMAGES) -> int:
    used = [int(m.group(1)) for p in images.glob("*.png") if (m := IMAGE_RE.match(p.name))]
    return max(used, default=0) + 1


def image_path(index: int, when: datetime, images: Path = IMAGES) -> Path:
    return images / f"{index:04d}_{when.strftime('%Y%m%d-%H%M%S')}.png"


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


@dataclass
class Manifest:
    data: dict

    @classmethod
    def new(cls, source_file: str, header_rows: int, real_rows: int) -> Manifest:
        return cls({
            "version": 1,
            "source": {"file": source_file, "header_rows": header_rows, "real_rows": real_rows},
            "units": "scene_units", "up_axis": "y",
            "steps": [],      # one entry per image, in order
            "parts": [],      # accepted parts only, in the order they joined current.ply
            "removed": [],    # accepted cleaning steps (indices removed from the pool)
        })

    @classmethod
    def load(cls, path: Path = MANIFEST) -> Manifest:
        return cls(orjson.loads(path.read_bytes()))

    def save(self, path: Path = MANIFEST) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_bytes(orjson.dumps(self.data, option=orjson.OPT_INDENT_2) + b"\n")
        tmp.replace(path)

    def add_step(self, **step) -> dict:
        self.data["steps"].append(step)
        return step

    def step(self, index: int) -> dict:
        return next(s for s in self.data["steps"] if s["index"] == index)

    def claimed_indices(self, root: Path = ROOT) -> np.ndarray:
        """Rows in accepted parts, concatenated in part order."""
        arrs = [np.load(root / p["indices"]) for p in self.data["parts"]]
        return np.concatenate(arrs) if arrs else np.empty(0, dtype=np.uint32)

    def removed_indices(self, root: Path = ROOT) -> np.ndarray:
        arrs = [np.load(root / r["indices"]) for r in self.data["removed"]]
        return np.concatenate(arrs) if arrs else np.empty(0, dtype=np.uint32)

    def pool_mask(self, root: Path = ROOT) -> np.ndarray:
        """True for rows not yet removed or claimed."""
        mask = np.ones(self.data["source"]["real_rows"], dtype=bool)
        mask[self.removed_indices(root)] = False
        mask[self.claimed_indices(root)] = False
        return mask
