"""Stage 7: what the detector did not name. The kept, non-structure splats that no instance owns are grouped by
density (DBSCAN on a 2 cm voxel grid); each big enough group becomes an instance with a shape-heuristic label.
Recall first: the challenge counts objects, and an honest "unidentified object" still gets a frame and metadata.
"""

from __future__ import annotations

import logging

import numpy as np
from sklearn.cluster import DBSCAN

from autoscene.lift import Instance
from autoscene.scene import Scene

log = logging.getLogger("autoscene.cluster")


def shape_label(pts: np.ndarray) -> tuple[str, dict]:
    """A label from the shape alone: PCA extents (p2..p98 along the principal axes)."""
    c = pts.mean(0)
    q = pts - c
    w, v = np.linalg.eigh(np.cov(q.T))
    order = np.argsort(-w)
    axes = v[:, order]
    proj = q @ axes
    ext = np.percentile(proj, 98, 0) - np.percentile(proj, 2, 0)        # e1 >= e2 >= e3
    e1, e2 = ext[0], ext[1]
    vertical = abs(axes[1, 0]) > 0.85
    info = {"extent_pca": [round(float(e), 3) for e in ext], "vertical": bool(vertical)}
    if e1 > 0.5 and e2 < 0.3 and e1 / max(e2, 1e-3) > 4:
        return ("column" if vertical else "pipe"), info
    if e1 > 2.0 and e2 > 1.0:
        return "pipe network", info
    if e1 < 0.35:
        return "small object", info
    return "unidentified object", info


def voxel_dbscan(sc: Scene, rows: np.ndarray, voxel: float = 0.02, eps: float = 0.05, min_samples: int = 5
                 ) -> tuple[np.ndarray, np.ndarray]:
    """DBSCAN on a voxel grid of the given splats: (label per splat, sizes per label)."""
    pts = sc.xyz[rows]
    key = np.floor(pts / voxel).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    centres = np.zeros((len(first), 3))
    np.add.at(centres, inv, pts)
    centres /= np.bincount(inv)[:, None]
    labels = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1).fit_predict(centres)
    lab_splat = labels[inv]
    sizes = np.bincount(lab_splat[lab_splat >= 0]) if (lab_splat >= 0).any() else np.zeros(0, int)
    return lab_splat, sizes


def add_clusters(sc: Scene, instances: list[Instance], voxel: float = 0.02, eps: float = 0.05, min_samples: int = 5,
                 min_splats: int = 300, min_extent: float = 0.12, pipe_split_above: int = 40_000) -> list[Instance]:
    """Residual splats -> density clusters; a cluster the size of the pipe network is split into pipe runs first,
    and what the splitter leaves (fittings, insulation surfaces) is clustered again by density."""
    owner = np.zeros(sc.n, dtype=bool)
    for ins in instances:
        owner[ins.splats] = True
    residual = np.flatnonzero(sc.keep & (sc.structure == 0) & ~owner)
    log.info("residual splats: %s", f"{len(residual):,}")
    out = list(instances)
    next_id = max((i.id for i in instances), default=-1) + 1
    added = 0

    def add(rows: np.ndarray, label: str, info: dict) -> None:
        nonlocal next_id, added
        out.append(Instance(next_id, rows.astype(np.int32), label, 0.3, {label: 0.3}, [], [], "cluster", info))
        next_id += 1
        added += 1

    def by_density(rows: np.ndarray, allow_split: bool) -> None:
        lab_splat, sizes = voxel_dbscan(sc, rows, voxel, eps, min_samples)
        for c in np.argsort(-sizes):
            if sizes[c] < min_splats:
                break
            part = rows[lab_splat == c]
            p = sc.xyz[part]
            if float(np.ptp(p, 0).max()) < min_extent:
                continue
            label, info = shape_label(p)
            if allow_split and (label == "pipe network" or sizes[c] >= pipe_split_above):
                pieces = split_pipes(sc, part)
                log.info("pipe network of %s splats split into %d pieces", f"{sizes[c]:,}", len(pieces))
                for piece, plabel, pinfo in pieces:
                    if plabel == "pipe network remainder":
                        by_density(piece, allow_split=False)
                    else:
                        add(piece, plabel, pinfo)
                continue
            add(part, label, info)

    by_density(residual, allow_split=True)
    log.info("%d clusters added from %s residual splats", added, f"{len(residual):,}")
    return out


# ---------------------------------------------------------------- pipe splitting for the big residual clusters


def local_directions(centres: np.ndarray, radius: float = 0.06) -> np.ndarray:
    """Unit principal direction of each point's neighbourhood (PCA of the neighbours within `radius`), with
    bincount sums (np.add.at is 50 x slower on the ~10 M pairs of a pipe network)."""
    from scipy.spatial import cKDTree
    n = len(centres)
    tree = cKDTree(centres)
    pairs = tree.query_pairs(radius, output_type="ndarray")
    i = np.concatenate([pairs[:, 0], pairs[:, 1], np.arange(n)])
    j = np.concatenate([pairs[:, 1], pairs[:, 0], np.arange(n)])
    cnt = np.bincount(i, minlength=n).astype(np.float64)
    mean = np.stack([np.bincount(i, weights=centres[j, k], minlength=n) for k in range(3)], 1) / cnt[:, None]
    d = centres[j] - mean[i]
    C = np.zeros((n, 3, 3))
    for a in range(3):
        for b in range(a, 3):
            C[:, a, b] = C[:, b, a] = np.bincount(i, weights=d[:, a] * d[:, b], minlength=n)
    _, v = np.linalg.eigh(C)
    return v[:, :, 2]


def smooth_classes(centres: np.ndarray, cls: np.ndarray, n_classes: int, radius: float = 0.05) -> np.ndarray:
    """Majority vote of each point's class among its neighbours (removes the flicker along a pipe)."""
    from scipy.spatial import cKDTree
    n = len(centres)
    pairs = cKDTree(centres).query_pairs(radius, output_type="ndarray")
    i = np.concatenate([pairs[:, 0], pairs[:, 1], np.arange(n)])
    j = np.concatenate([pairs[:, 1], pairs[:, 0], np.arange(n)])
    votes = np.stack([np.bincount(i, weights=(cls[j] == k).astype(np.float64), minlength=n) for k in range(n_classes)], 1)
    return votes.argmax(1).astype(np.int8)


def split_pipes(sc: Scene, rows: np.ndarray, voxel: float = 0.02, radius: float = 0.12, eps: float = 0.03,
                min_piece: int = 400, axis_min: float = 0.75, coarse: float = 0.04) -> list[tuple[np.ndarray, str, dict]]:
    """Break a pipe network into runs: every voxel gets the axis its neighbourhood runs along (x, y, z or none),
    and the connected pieces (at `eps`) of each axis class become objects. Returns (rows, label, info) tuples;
    the remainder (pieces under `min_piece`) comes back as one 'pipe network remainder'."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    pts = sc.xyz[rows]
    key = np.floor(pts / voxel).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    centres = np.zeros((len(first), 3))
    np.add.at(centres, inv, pts)
    centres /= np.bincount(inv)[:, None]
    # directions on a coarser grid (4 cm) for speed, then every fine voxel takes its coarse voxel's class
    ckey = np.floor(centres / coarse).astype(np.int64)
    _, cinv = np.unique(ckey, axis=0, return_inverse=True)
    ccentres = np.zeros((cinv.max() + 1, 3))
    np.add.at(ccentres, cinv, centres)
    ccentres /= np.bincount(cinv)[:, None]
    dirs = np.abs(local_directions(ccentres, radius))
    ccls = np.full(len(ccentres), 3, np.int8)               # 3 = no clear axis (elbows, tees, valves)
    for k in (0, 2, 1):
        ccls[dirs[:, k] >= axis_min] = k
    ccls = smooth_classes(ccentres, ccls, 4, radius=1.5 * coarse)
    cls = ccls[cinv]
    out: list[tuple[np.ndarray, str, dict]] = []
    leftover = np.zeros(len(centres), bool)
    names = {0: "pipe", 1: "vertical pipe", 2: "pipe", 3: "pipe fitting"}
    for k in range(4):
        sel = np.flatnonzero(cls == k)
        if len(sel) == 0:
            continue
        tree = cKDTree(centres[sel])
        pairs = tree.query_pairs(eps, output_type="ndarray")
        G = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(sel),) * 2)
        _, comp = connected_components(G, directed=False)
        vox_comp = np.full(len(centres), -1, np.int64)
        vox_comp[sel] = comp
        splat_comp = vox_comp[inv]
        sizes = np.bincount(splat_comp[splat_comp >= 0]) if (splat_comp >= 0).any() else np.zeros(0, int)
        for c in np.argsort(-sizes):
            if sizes[c] < min_piece:
                leftover[sel[comp == c]] = True
                continue
            piece = rows[splat_comp == c]
            p = sc.xyz[piece]
            ext = np.ptp(p, 0)
            info = {"axis": "xyz-"[k], "extent": [round(float(e), 3) for e in ext]}
            label = names[k]
            if k in (0, 2) and ext[k] < 0.5:
                label = "pipe fitting"
            out.append((piece.astype(np.int32), label, info))
    rest = rows[leftover[inv]]
    if len(rest) >= 1000:
        out.append((rest.astype(np.int32), "pipe network remainder", {"extent": [round(float(e), 3)
                                                                                 for e in np.ptp(sc.xyz[rest], 0)]}))
    return out
