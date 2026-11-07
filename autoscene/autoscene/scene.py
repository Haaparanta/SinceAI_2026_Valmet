"""Stage 1-3: the scan in memory, automatic cleaning, and the room structure (floor, ceiling, walls).

Everything here is geometry on splat centres: no model, no human. The thresholds come from the manual build of the
same scan (branch claude/equipment-room-splat-30s), where a person accepted each of them picture by picture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from autoscene import DATA
from autoscene.geometry import ceiling_height_by_cells, ceiling_split, fit_floor_plane
from autoscene.orientation import FRAME
from autoscene.splats import alpha_of, load_real_splats, rgb_of, size_of, xyz_of

log = logging.getLogger("autoscene.scene")

STRUCTURE_NAMES = {0: "", 1: "floor", 2: "ceiling", 3: "wall_back", 4: "wall_front", 5: "wall_left", 6: "wall_right"}


def cache_for(ply: Path) -> Path:
    stem = "".join(c if c.isalnum() else "_" for c in ply.stem).strip("_")
    return DATA / "cache" / f"real_sh0_{FRAME}_{stem}_{ply.stat().st_size}.npy"


@dataclass
class Scene:
    splats: np.ndarray                      # SH0 structured array, world frame, every real row of the source
    source: str
    xyz: np.ndarray = field(init=False)     # float32[n, 3]
    rgb: np.ndarray = field(init=False)     # uint8[n, 3]
    alpha: np.ndarray = field(init=False)
    size: np.ndarray = field(init=False)
    keep: np.ndarray = field(init=False)    # bool[n]: survives cleaning
    structure: np.ndarray = field(init=False)   # int8[n]: STRUCTURE_NAMES key, 0 = not structure
    floor_plane: tuple[float, float, float] = (0.0, 0.0, 0.0)   # y = a x + b z + c
    floor_rms: float = 0.0
    ceiling_y: float = 0.0
    walls: dict[str, float] = field(default_factory=dict)       # back/front = z, left/right = x
    bmin: np.ndarray = field(init=False)    # p1..p99 room bounds of the kept points (fixed framing for images)
    bmax: np.ndarray = field(init=False)
    info: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.xyz = xyz_of(self.splats)
        self.rgb = rgb_of(self.splats)
        self.alpha = alpha_of(self.splats)
        self.size = size_of(self.splats)
        self.keep = np.ones(len(self.splats), dtype=bool)
        self.structure = np.zeros(len(self.splats), dtype=np.int8)
        self.bmin, self.bmax = np.percentile(self.xyz, 1, axis=0), np.percentile(self.xyz, 99, axis=0)

    @property
    def n(self) -> int:
        return len(self.splats)

    def floor_y_at(self, xyz: np.ndarray) -> np.ndarray:
        a, b, c = self.floor_plane
        return a * xyz[:, 0] + b * xyz[:, 2] + c

    def kept_idx(self) -> np.ndarray:
        return np.flatnonzero(self.keep)

    def free_idx(self) -> np.ndarray:
        """Kept splats that are not structure: the pool the detector and the clustering work on."""
        return np.flatnonzero(self.keep & (self.structure == 0))


def load(ply: Path) -> Scene:
    s = load_real_splats(ply, cache_for(ply))
    log.info("loaded %s splats from %s", f"{len(s):,}", ply.name)
    return Scene(s, ply.name)


# ---------------------------------------------------------------- stage 2: cleaning


def wall_edge(values: np.ndarray, high: bool, bin_size: float = 0.05, rel: float = 0.2) -> float:
    """Outer face of the outermost dense layer along one axis: the farthest `bin_size` bin (on that side) holding at
    least `rel` x the axis' densest bin. Walls are dense layers; floaters behind them are not. On this scan the back
    wall is the -3.70 layer (37,864 splats), not the equipment layer at -3.41 that envelope_edge picked."""
    v = values if high else -values
    lo, hi = np.percentile(v, [0.05, 99.95])
    counts, e = np.histogram(v, bins=np.arange(lo, hi + bin_size, bin_size))
    k = int(np.flatnonzero(counts >= rel * counts.max())[-1])
    edge = float(e[k + 1])
    return edge if high else -edge


def clean(sc: Scene, floor_margin: float = 0.04, wall_margin: float = 0.06, ceiling_margin: float = 0.08,
          lone_radius: float = 0.06, lone_min: int = 4) -> Scene:
    """Automatic cleaning. Removes (in this order, each on what is left):
    1. everything more than `floor_margin` under the fitted floor plane (mirror images in the glossy floor),
    2. everything beyond a wall + `wall_margin` on the four sides (floaters behind the walls),
    3. everything above the ceiling + `ceiling_margin`,
    4. lone splats with fewer than `lone_min` neighbours within `lone_radius` (fog, strays)."""
    xyz = sc.xyz
    a, b, c, rms = fit_floor_plane(xyz)
    sc.floor_plane, sc.floor_rms = (a, b, c), rms
    plane_y = sc.floor_y_at(xyz)
    below = xyz[:, 1] < plane_y - floor_margin
    keep = ~below
    log.info("floor plane y = %+.4f x %+.4f z %+.3f (rms %.3f); below floor: %s", a, b, c, rms, f"{below.sum():,}")

    p = xyz[keep]
    walls = {
        "back": wall_edge(p[:, 2], high=False), "front": wall_edge(p[:, 2], high=True),
        "left": wall_edge(p[:, 0], high=False), "right": wall_edge(p[:, 0], high=True),
    }
    sc.walls = walls
    outside = ((xyz[:, 2] < walls["back"] - wall_margin) | (xyz[:, 2] > walls["front"] + wall_margin)
               | (xyz[:, 0] < walls["left"] - wall_margin) | (xyz[:, 0] > walls["right"] + wall_margin))
    outside &= keep
    keep &= ~outside
    log.info("walls x %+.2f..%+.2f, z %+.2f..%+.2f; outside: %s", walls["left"], walls["right"], walls["back"],
             walls["front"], f"{outside.sum():,}")

    p = xyz[keep]
    split_y, _ = ceiling_split(p[:, 1])
    ceiling_y, cells, near = ceiling_height_by_cells(p, split_y)
    sc.ceiling_y = ceiling_y
    above = keep & (xyz[:, 1] > ceiling_y + ceiling_margin)
    keep &= ~above
    log.info("ceiling y %+.3f (%d/%d cells agree); above: %s", ceiling_y, near, cells, f"{above.sum():,}")

    idx = np.flatnonzero(keep)
    tree = cKDTree(xyz[idx])
    counts = tree.query_ball_point(xyz[idx], r=lone_radius, return_length=True, workers=-1)
    lone = counts < lone_min
    keep[idx[lone]] = False
    log.info("lone splats: %s", f"{lone.sum():,}")

    sc.keep = keep
    kept = xyz[keep]
    sc.bmin, sc.bmax = np.percentile(kept, 1, axis=0), np.percentile(kept, 99, axis=0)
    sc.info["clean"] = {
        "below_floor": int(below.sum()), "outside_walls": int(outside.sum()), "above_ceiling": int(above.sum()),
        "lone": int(lone.sum()), "kept": int(keep.sum()), "of": int(sc.n),
        "floor_plane": [round(a, 6), round(b, 6), round(c, 4)], "floor_rms": round(rms, 4),
        "walls": {k: round(v, 4) for k, v in walls.items()}, "ceiling_y": round(ceiling_y, 4),
    }
    return sc


# ---------------------------------------------------------------- stage 3: structure


def structure(sc: Scene, floor_above: float = 0.025, ceiling_below: float = 0.03, wall_depth: float = 0.10,
              lamp_white: int = 240) -> Scene:
    """Label floor, ceiling and the four walls among the kept splats.
    floor: at or below the fitted plane + `floor_above` (2 x its RMS). ceiling: from `ceiling_below` under the
    measured ceiling height up, except saturated-white splats (lamps hang from the ceiling and stay objects).
    walls: within `wall_depth` of the envelope on each side, between floor and ceiling, except splats whose
    neighbourhood sticks out into the room (equipment standing against the wall keeps its own splats)."""
    xyz, keep = sc.xyz, sc.keep
    lab = np.zeros(sc.n, dtype=np.int8)
    plane_y = sc.floor_y_at(xyz)
    floor = keep & (xyz[:, 1] <= plane_y + floor_above)
    lab[floor] = 1
    lamp = sc.rgb.min(1) >= lamp_white
    ceiling = keep & (lab == 0) & (xyz[:, 1] >= sc.ceiling_y - ceiling_below) & ~lamp
    lab[ceiling] = 2
    w = sc.walls
    for code, side, axis, sign in ((3, "back", 2, -1), (4, "front", 2, +1), (5, "left", 0, -1), (6, "right", 0, +1)):
        d = (xyz[:, axis] - w[side]) * sign            # > 0 = beyond the wall, < 0 = into the room
        cand = keep & (lab == 0) & (d >= -wall_depth)
        lab[cand] = code
    sc.structure = lab
    counts = {STRUCTURE_NAMES[k]: int((lab == k).sum()) for k in range(1, 7)}
    sc.info["structure"] = counts
    log.info("structure: %s", counts)
    return sc


# ---------------------------------------------------------------- persistence


def save_state(sc: Scene, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, keep=sc.keep, structure=sc.structure, floor_plane=np.array(sc.floor_plane),
                        floor_rms=sc.floor_rms, ceiling_y=sc.ceiling_y,
                        walls=np.array([sc.walls[k] for k in ("back", "front", "left", "right")]),
                        bmin=sc.bmin, bmax=sc.bmax)


def load_state(sc: Scene, path: Path) -> Scene:
    z = np.load(path)
    sc.keep, sc.structure = z["keep"], z["structure"]
    sc.floor_plane = tuple(float(v) for v in z["floor_plane"])
    sc.floor_rms, sc.ceiling_y = float(z["floor_rms"]), float(z["ceiling_y"])
    sc.walls = dict(zip(("back", "front", "left", "right"), (float(v) for v in z["walls"])))
    sc.bmin, sc.bmax = z["bmin"], z["bmax"]
    return sc
