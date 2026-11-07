"""Stage 6: 2D detections (each already a set of splat ids) -> 3D instances.

View consensus in the spirit of MaskClustering / SAI3D: two masks from different views that share most of their
splats are the same object; union-find over those links makes instances; every splat goes to the instance that saw
it most often; instances seen from fewer than `min_views` views are dropped; the splats no view saw (undersides,
insides) are filled in from their nearest labelled neighbours; each instance is then split into its spatially
connected pieces.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from autoscene.detect2d import Detection
from autoscene.scene import Scene

log = logging.getLogger("autoscene.lift")


@dataclass
class Instance:
    id: int
    splats: np.ndarray                      # int32 row indices into the scene
    label: str
    confidence: float                       # 0..1
    scores: dict[str, float] = field(default_factory=dict)   # label -> summed score over its masks
    views: list[int] = field(default_factory=list)           # view indices that saw it
    detections: list[int] = field(default_factory=list)      # indices into the detection list
    source: str = "yoloe"                   # yoloe | cluster | structure
    info: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.splats)


def visibility(views_dir, n_splats: int, min_weight_pixels: int = 1) -> sparse.csr_matrix:
    """Vis[view, splat] = 1 when the splat made at least one pixel of that view (from the saved ID buffers)."""
    import json
    names = [m["name"] for m in json.loads((views_dir / "views.json").read_text())["views"]]
    rows, cols = [], []
    for v, name in enumerate(names):
        ids = np.load(views_dir / f"{name}.ids.npz")["ids"]
        u = np.unique(ids[ids >= 0])
        rows.append(np.full(len(u), v, np.int32))
        cols.append(u.astype(np.int32))
    r, c = np.concatenate(rows), np.concatenate(cols)
    return sparse.csr_matrix((np.ones(len(r), np.float32), (r, c)), shape=(len(names), n_splats))


def link_masks(dets: list[Detection], n_splats: int, vis: sparse.csr_matrix | None = None, min_overlap: float = 0.5,
               min_size_ratio: float = 0.25, min_splats: int = 30, min_visible: float = 0.3,
               min_consensus: float = 0.5) -> tuple[np.ndarray, sparse.csr_matrix]:
    """Union-find labels over detections. Det i and j (different views) are candidates when they share at least
    `min_overlap` of the smaller one's splats and the smaller is at least `min_size_ratio` of the larger (a gauge
    seen inside a pipe mask is not the pipe). With `vis` (views x splats) the MaskClustering view-consensus test
    is added: among the views that see at least `min_visible` of both masks' splats, the share that put both into
    ONE mask must be at least `min_consensus`; two ladders side by side are then never chained together through a
    third view's mask that covers both."""
    rows, cols = [], []
    for k, d in enumerate(dets):
        rows.append(np.full(len(d.splat_ids), k, np.int32))
        cols.append(d.splat_ids)
    M = sparse.csr_matrix((np.ones(sum(len(r) for r in rows), np.float32), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(len(dets), n_splats))
    sizes = np.asarray(M.sum(1)).ravel()
    O = (M @ M.T).tocoo()
    i, j, shared = O.row, O.col, O.data
    keep = i < j
    i, j, shared = i[keep], j[keep], shared[keep]
    view = np.array([d.view for d in dets])
    small = np.minimum(sizes[i], sizes[j])
    big = np.maximum(sizes[i], sizes[j])
    ok = (view[i] != view[j]) & (small >= min_splats) & (shared / np.maximum(small, 1) >= min_overlap) \
        & (small / np.maximum(big, 1) >= min_size_ratio)
    n_cand = int(ok.sum())
    if vis is not None and n_cand:
        n_views = vis.shape[0]
        # fvis[mask, view]: share of the mask's splats visible in the view
        fvis = np.asarray((M @ vis.T).todense()) / np.maximum(sizes, 1)[:, None]
        # best[mask, view]: the mask of that view holding the largest share of this mask's visible splats, and that share
        Of = (M @ M.T).tocsr()
        best = np.full((len(dets), n_views), -1, np.int32)
        cont = np.zeros((len(dets), n_views), np.float32)
        Oc = Of.tocoo()
        a, b, sh = Oc.row, Oc.col, Oc.data
        vb = view[b]
        visible_cnt = fvis[a, vb] * sizes[a]
        share = sh / np.maximum(visible_cnt, 1)
        order = np.lexsort((-share, vb, a))
        a, vb, b, share = a[order], vb[order], b[order], share[order]
        first = np.ones(len(a), bool)
        first[1:] = (a[1:] != a[:-1]) | (vb[1:] != vb[:-1])
        best[a[first], vb[first]] = b[first]
        cont[a[first], vb[first]] = share[first]
        ci, cj = i[ok], j[ok]
        observing = (fvis[ci] >= min_visible) & (fvis[cj] >= min_visible)          # pairs x views
        agree = observing & (best[ci] == best[cj]) & (best[ci] >= 0) & (cont[ci] >= 0.5) & (cont[cj] >= 0.5)
        n_obs = observing.sum(1)
        consensus = np.where(n_obs > 0, agree.sum(1) / np.maximum(n_obs, 1), 1.0)   # unobserved pairs: keep the overlap link
        passed = consensus >= min_consensus
        ok_idx = np.flatnonzero(ok)
        ok[ok_idx[~passed]] = False
        log.info("view consensus: %d of %d candidate links kept", int(passed.sum()), n_cand)
    if vis is not None:
        from autoscene.merge import merge_masks
        comp = merge_masks(M, view, vis, min_overlap=min_overlap, min_visible=min_visible, min_consensus=min_consensus,
                           min_splats=min_splats)
        log.info("%d masks -> %d groups (greedy consensus merging)", len(dets), len(np.unique(comp)))
        return comp, M
    G = sparse.coo_matrix((np.ones(int(ok.sum())), (i[ok], j[ok])), shape=(len(dets), len(dets)))
    _, comp = connected_components(G, directed=False)
    log.info("%d masks, %d links, %d groups", len(dets), int(ok.sum()), len(np.unique(comp)))
    return comp, M


def vote(dets: list[Detection], comp: np.ndarray, M: sparse.csr_matrix, min_views: int = 2,
         min_splats: int = 150) -> list[Instance]:
    """Every splat goes to the group that saw it in the most masks. Groups seen from < `min_views` views or ending
    up with < `min_splats` splats are dropped (hallucinated single-view masks)."""
    n_groups = int(comp.max()) + 1
    groups_of = sparse.csr_matrix((np.ones(len(dets), np.float32), (np.arange(len(dets)), comp)),
                                  shape=(len(dets), n_groups))
    votes = (M.T @ groups_of).tocsr()                       # splats x groups
    votes.sum_duplicates()
    best = np.asarray(votes.argmax(axis=1)).ravel()
    best_v = np.asarray(votes.max(axis=1).todense()).ravel()
    seen = best_v > 0
    group_views = defaultdict(set)
    for k, d in enumerate(dets):
        group_views[int(comp[k])].add(d.view)
    out: list[Instance] = []
    for g in range(n_groups):
        if len(group_views[g]) < min_views:
            continue
        splats = np.flatnonzero(seen & (best == g)).astype(np.int32)
        if len(splats) < min_splats:
            continue
        members = np.flatnonzero(comp == g)
        scores: dict[str, float] = defaultdict(float)
        for k in members:
            scores[dets[k].label] += dets[k].score
        label = max(scores, key=scores.get)
        conf = float(min(1.0, scores[label] / max(len(members), 1) + 0.1 * min(len(group_views[g]), 5) / 5))
        out.append(Instance(len(out), splats, label, conf, dict(scores), sorted(group_views[g]),
                            [int(k) for k in members]))
    log.info("%d instances after the vote", len(out))
    return out


def fill_unseen(sc: Scene, instances: list[Instance], seen: np.ndarray | None = None, radius: float = 0.03,
                passes: int = 3) -> list[Instance]:
    """Splats no view saw (inside, underside, hidden behind a neighbour) take the instance of their nearest
    labelled neighbour within `radius`, for `passes` rounds. Splats that some view did see but no mask claimed stay
    unclaimed (they belong to something the detector did not name); structure splats are never filled."""
    owner = np.full(sc.n, -1, np.int32)
    for ins in instances:
        owner[ins.splats] = ins.id
    free = sc.keep & (sc.structure == 0)
    if seen is not None:
        free &= ~seen
    for _ in range(passes):
        have = np.flatnonzero(owner >= 0)
        want = np.flatnonzero(free & (owner < 0))
        if len(have) == 0 or len(want) == 0:
            break
        tree = cKDTree(sc.xyz[have])
        d, k = tree.query(sc.xyz[want], k=1, distance_upper_bound=radius, workers=-1)
        hit = np.isfinite(d)
        owner[want[hit]] = owner[have[k[hit]]]
        log.info("fill: %s splats joined an instance", f"{int(hit.sum()):,}")
    for ins in instances:
        ins.splats = np.flatnonzero(owner == ins.id).astype(np.int32)
    return instances


def split_connected(sc: Scene, instances: list[Instance], eps: float = 0.15, min_part: int = 250,
                    voxel: float = 0.02, min_share: float = 0.05) -> list[Instance]:
    """Split each instance into its spatially connected pieces (single-linkage at `eps` on a `voxel` grid; 15 cm so
    a wire cage or a ladder stays one piece). Pieces smaller than `min_part` splats are dropped (fragments of other
    objects in the masks)."""
    out: list[Instance] = []
    for ins in instances:
        pts = sc.xyz[ins.splats]
        key = np.floor(pts / voxel).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        centres = np.zeros((inv.max() + 1, 3))
        np.add.at(centres, inv, pts)
        counts = np.bincount(inv)
        centres /= counts[:, None]
        tree = cKDTree(centres)
        pairs = tree.query_pairs(eps, output_type="ndarray")
        G = sparse.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(centres),) * 2)
        _, comp = connected_components(G, directed=False)
        comp_of_splat = comp[inv]
        sizes = np.bincount(comp_of_splat)
        order = np.argsort(-sizes)
        for c in order:
            if sizes[c] < min_part or (sizes[c] < min_share * len(ins.splats) and sizes[c] < 1000):
                break
            part = ins.splats[comp_of_splat == c]
            out.append(Instance(len(out), part, ins.label, ins.confidence, dict(ins.scores), list(ins.views),
                                list(ins.detections), ins.source, dict(ins.info)))
    log.info("%d instances after the connectivity split", len(out))
    return out


def lift(sc: Scene, dets: list[Detection], min_views: int = 2, seen: np.ndarray | None = None,
         vis: sparse.csr_matrix | None = None) -> list[Instance]:
    dets = [d for d in dets if d.splat_ids is not None and len(d.splat_ids) >= 30]
    comp, M = link_masks(dets, sc.n, vis)
    instances = vote(dets, comp, M, min_views=min_views)
    instances = fill_unseen(sc, instances, seen)
    instances = split_connected(sc, instances)
    for ins in instances:
        ins.info["label_votes"] = Counter({k: round(v, 2) for k, v in ins.scores.items()}).most_common(3)
    return instances


def save_instances(instances: list[Instance], path) -> None:
    import orjson
    table = [{"id": i.id, "label": i.label, "confidence": round(i.confidence, 3), "n": i.n, "source": i.source,
              "scores": {k: round(v, 3) for k, v in i.scores.items()}, "views": i.views,
              "detections": i.detections, "info": i.info} for i in instances]
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, splats=np.concatenate([i.splats for i in instances]) if instances else np.zeros(0, np.int32),
                        sizes=np.array([i.n for i in instances]), table=orjson.dumps(table))


def load_instances(path) -> list[Instance]:
    import orjson
    z = np.load(path)
    table = orjson.loads(bytes(z["table"]))
    out, pos = [], 0
    for row, n in zip(table, z["sizes"]):
        out.append(Instance(row["id"], z["splats"][pos:pos + int(n)], row["label"], row["confidence"], row["scores"],
                            row["views"], row["detections"], row["source"], row["info"]))
        pos += int(n)
    return out
