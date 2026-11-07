"""Greedy view-consensus merging of 2D masks into 3D object groups (the MaskClustering idea, done at group level).

Union-find chains objects: ladder A links to a mask that covers A and B, which links to ladder B. Here groups grow
one merge at a time and every merge is re-checked against the views: two groups join only when, among the views
that see enough of both, at least `min_consensus` put both into ONE mask (ties between a tight and a loose mask go
to the tight one, so a gauge on a pipe keeps its own group).
"""

from __future__ import annotations

import logging

import numpy as np
from scipy import sparse

log = logging.getLogger("autoscene.merge")


def _best_mask_per_view(Gm: sparse.csr_matrix, M: sparse.csr_matrix, view: np.ndarray, msize: np.ndarray,
                        fvis: np.ndarray, gsize: np.ndarray, n_views: int) -> tuple[np.ndarray, np.ndarray]:
    """best[g, v]: the mask of view v holding the largest share of group g's splats visible in v (tie -> the
    smaller mask); cont[g, v]: that share."""
    G = Gm.shape[0]
    GM = (Gm @ M.T).tocoo()
    g, m, sh = GM.row, GM.col, GM.data
    vm = view[m]
    visible_cnt = fvis[g, vm] * gsize[g]
    share = sh / np.maximum(visible_cnt, 1)
    order = np.lexsort((msize[m], -share, vm, g))
    g, vm, m, share = g[order], vm[order], m[order], share[order]
    first = np.ones(len(g), bool)
    first[1:] = (g[1:] != g[:-1]) | (vm[1:] != vm[:-1])
    best = np.full((G, n_views), -1, np.int32)
    cont = np.zeros((G, n_views), np.float32)
    best[g[first], vm[first]] = m[first]
    cont[g[first], vm[first]] = share[first]
    return best, cont


def merge_masks(M: sparse.csr_matrix, view: np.ndarray, vis: sparse.csr_matrix, min_overlap: float = 0.5,
                min_size_ratio: float = 0.1, min_visible: float = 0.3, min_consensus: float = 0.5,
                min_splats: int = 30, rounds: int = 15) -> np.ndarray:
    """Group label per mask. M: masks x splats (binary), view: view index per mask, vis: views x splats."""
    n = M.shape[0]
    n_views = vis.shape[0]
    msize = np.asarray(M.sum(1)).ravel()
    comp = np.arange(n)
    for r in range(rounds):
        groups, comp = np.unique(comp, return_inverse=True)
        G = len(groups)
        Gm = sparse.csr_matrix((np.ones(n, np.float32), (comp, np.arange(n))), shape=(G, n)) @ M
        Gm.data[:] = 1.0
        gsize = np.asarray(Gm.sum(1)).ravel()
        fvis = np.asarray((Gm @ vis.T).todense()) / np.maximum(gsize, 1)[:, None]
        best, cont = _best_mask_per_view(Gm, M, view, msize, fvis, gsize, n_views)
        O = (Gm @ Gm.T).tocoo()
        i, j, shared = O.row, O.col, O.data
        keep = i < j
        i, j, shared = i[keep], j[keep], shared[keep]
        small, big = np.minimum(gsize[i], gsize[j]), np.maximum(gsize[i], gsize[j])
        overlap = shared / np.maximum(small, 1)
        ok = (small >= min_splats) & (overlap >= min_overlap) & (small / np.maximum(big, 1) >= min_size_ratio)
        i, j, overlap = i[ok], j[ok], overlap[ok]
        if len(i) == 0:
            break
        observing = (fvis[i] >= min_visible) & (fvis[j] >= min_visible)
        agree = observing & (best[i] == best[j]) & (best[i] >= 0) & (cont[i] >= 0.5) & (cont[j] >= 0.5)
        n_obs = observing.sum(1)
        consensus = np.where(n_obs > 0, agree.sum(1) / np.maximum(n_obs, 1), overlap)
        passed = consensus >= min_consensus
        i, j, consensus, overlap = i[passed], j[passed], consensus[passed], overlap[passed]
        order = np.lexsort((-overlap, -consensus))
        taken = np.zeros(G, bool)
        parent = np.arange(G)
        merges = 0
        for a, b in zip(i[order], j[order]):
            if taken[a] or taken[b]:
                continue
            taken[a] = taken[b] = True
            parent[b] = a
            merges += 1
        log.info("round %d: %d groups, %d candidate pairs, %d passed consensus, %d merged", r + 1, G, int(ok.sum()),
                 int(passed.sum()), merges)
        if merges == 0:
            break
        comp = parent[comp]
    _, comp = np.unique(comp, return_inverse=True)
    return comp
