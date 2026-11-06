`// VALMET × SINCE AI 2026 · RESEARCH · 02`

# 02: Semantic asset extraction and 3D framing on a Mac, in 36 hours

Criterion c1 (30 %) rewards the number of objects we cut out of the scan and frame in 3D. The fastest safe path is a pure-geometry pipeline (planes out, pipes peeled off as cylinders, the rest clustered and boxed) that runs on CPU by Saturday morning. On top of it we add a "render many views → 2D segment and detect → vote back onto gaussian IDs → merge" lift that runs on Apple-silicon MPS. Every proposal goes to the human curator, so we tune for recall and let approvals clean up precision.

`2026-11-06 · INPUT: ~500 k clean gaussians (see 01) · TARGET MACHINE: Apple M1, 8 GB RAM, torch MPS available, no CUDA, no Ollama yet`

---

## 1. Recommendation

### Tier 0: geometric baseline (done by Sat 2026-11-07 ~09:00)

CPU only. Open3D + scikit-learn + pyRANSAC-3D + numpy. Expected output: **80–200 proposals** [UNVERIFIED: depends on scan density].

1. Load the cleaned centres (`01_clean` output). Voxel-downsample to ~2 cm in scene units. Keep a map from each voxel point back to its gaussian indices.
2. **Remove the structure.** Run RANSAC on planes with a y-up prior. The lowest large horizontal plane is the floor (≈ y −0.9). The highest is the ceiling. Large vertical planes are walls. Save them as "structure" assets (floor, wall N/E/S/W, ceiling). They count as framed objects and the router needs them.
3. **Peel pipes.** Run iterative RANSAC cylinders on what is left. Accept a cylinder if the radius is in range, the inliers are long along the axis, and the inlier density is high. Split each accepted cylinder into connected runs along its axis. Each run becomes a `pipe` asset with an axis-aligned OBB. This step matters most: pipes glue everything into one giant cluster.
4. **Cluster the rest.** Run DBSCAN (Open3D `cluster_dbscan`) on xyz. Re-split any cluster bigger than ~1.5 m³ with HDBSCAN on `xyz + 0.3·rgb`, or with a smaller `eps`.
5. **Frame each cluster.** Use a gravity-aligned OBB: y stays vertical, yaw comes from PCA on the xz footprint. This looks right in a boiler room and is stable. Keep `create_from_points_minimal` only for pipes and tilted parts.
6. **Heuristic label** from shape (table in §3.4). The curator can edit the label.
7. Write `proposals.json`: `id, label, label_source, confidence, obb{center,R,extent}, gaussian_ids, n_points, thumbnail.png`.

### Tier 1: multi-view 2D → 3D lift (Sat daytime, target by Sat 20:00)

MPS where possible. Expected gain: smaller objects (valves, gauges, motors, cabinets) that geometry merges into their neighbours, plus real class names.

1. **Render ~60–150 views** of the cleaned gaussians with our own numpy z-buffer renderer. It writes an **RGB image and an ID buffer** (gaussian index per pixel). The cameras sit on a ring at eye height (y ≈ floor + 1.6) looking inwards, plus a few top-down and pipe-rack views.
2. **2D proposals per view**, best first:
   - **SAM 2.1 automatic mask generator** (class-agnostic, high recall), or **SAM 3** with text prompts ("valve", "pump", "electric motor", "pressure gauge", "pipe", "control cabinet", "ladder", "tank", "boiler") when it runs on MPS.
   - Fallback/complement: **OWLv2** or **Florence-2 `<OD>` / `<OPEN_VOCABULARY_DETECTION>`** for boxes, then box-prompt SAM for masks.
3. **Back-project.** Each mask → set of gaussian IDs visible under its pixels. No ray casting is needed: the ID buffer already answers it.
4. **Merge across views** with a mask graph (a simplified MaskClustering "view consensus"): link two masks when their ID sets overlap enough. Run union-find. Each gaussian then takes the majority instance across the views that saw it.
5. **Reconcile with tier 0.** Tier-1 instances that sit inside a tier-0 cluster split it. Tier-1 instances with no tier-0 match become new proposals. Remove duplicates by 3D IoU > 0.5.
6. **Label** each instance with CLIP zero-shot on its best-view crop (largest visible mask area). Send the uncertain ones (top-1 margin < 0.1) to a small VLM.

### Tier 2: stretch (only if tiers 0–1 are solid by Sat night)

- **VLM relabel and description** of every approved object with Qwen2.5-VL 3B (Ollama or MLX). Ask for a strict JSON `{label, confidence, short_description}`. 3B fits in 8 GB; 7B is tight [UNVERIFIED on this M1].
- **Per-object meshes** (see 04) or a "SAM 3D Objects" mesh from the best crop for the hero asset (P-005). It is GPU-heavy, so treat it as a slide extra, not a pipeline step.
- **Pipe network graph**: join cylinder runs at elbows and tees. Show "pipe run PR-03 connects pump P-005 to boiler B-01". This is cheap and impressive.
- **Sonata/PTv3 features** for clustering. Skip unless someone has a CUDA box: the stack expects spconv/flash-attn [UNVERIFIED on Mac].

### What we skip, and why

Gaussian-native segmenters (Gaussian Grouping, SAGA, Gaga, LangSplat, Feature 3DGS, OpenGaussian) and the 3D-instance research stacks (MaskClustering, Open3DIS, OpenMask3D, SAI3D, Mask3D, OneFormer3D). They need **CUDA** and the **original training images with camera poses**, and we only have the PLY. The fly-through mp4 has no poses; registering it with COLMAP and then aligning to the splat is a day of risk. We borrow their *ideas* (ID-buffer voting, view-consensus merging), not their code.

---

## 2. Options compared

| Option | What it gives | GPU needed? | Apple silicon / MPS | Setup time | Expected quality on this industrial scene |
|---|---|---|---|---|---|
| Open3D `segment_plane` + `cluster_dbscan` + OBB | floor/walls, blobs, boxes | No | CPU wheel 0.20 on arm64; **needs `brew install libusb`** (verified failing import without it) | 30 min | Good for big equipment; merges touching objects |
| pyRANSAC-3D `Cylinder` / `Plane` | pipes, tanks, vertical vessels | No | Pure numpy | 15 min | Good on clean straight pipes; slow on big inputs, so subsample |
| scikit-learn `HDBSCAN` | variable-density clusters | No | Yes (sklearn 1.9 verified) | 5 min | Better than DBSCAN in dense corners; memory heavy above ~200 k pts |
| Cut-pursuit / superpoints | geometric over-segmentation | No | C++ build, cmake | 1–3 h | Nice superpoints, but the build risk is not worth it |
| Region growing (normals + curvature) | smooth-surface segments | No | numpy/Open3D normals | 2 h to hand-roll | Fine; we only need it if DBSCAN under-splits |
| SAM 2.1 auto masks on rendered views | class-agnostic 2D masks | Helps | MPS works per SAM 2 README [UNVERIFIED]; CPU slow | 1 h | High recall; renders of points are noisier than photos |
| **SAM 3** (text + exemplar prompts) | open-vocab masks with names | Helps | Not clean yet: needs transformers main or patches (PR #400, issue #173); MLX ports exist | 2–4 h | Best 2D option if it runs; budget a fallback |
| OWLv2 / OWL-ViT (transformers) | open-vocab boxes | Helps | MPS/CPU via transformers | 30 min | Decent recall on "pipe/valve/tank", weak on small gauges [UNVERIFIED] |
| Florence-2 base/large (0.23 B / 0.77 B) | `<OD>`, open-vocab detection, captions | Helps | MPS reported (FiftyOne device pick) | 45 min | Small and fast; COCO-ish vocabulary |
| Grounding DINO | open-vocab boxes | Helps | CPU/MPS via transformers, slow [UNVERIFIED] | 1 h | Good with prompts; slower than OWLv2 |
| CLIP / OpenCLIP zero-shot on crops | label per cluster | No | MPS fine | 20 min | Good for coarse classes (pipe, tank, valve, cabinet) |
| Qwen2.5-VL 3B / Moondream (Ollama or MLX) | label + description + optional boxes | Helps | Ollama Metal / MLX; Ollama **not installed** yet | 30 min + download | Best labels; ~2–10 s per crop on M1 [UNVERIFIED] |
| Gaussian Grouping / SAGA / Gaga / LangSplat / Feature 3DGS / OpenGaussian | per-gaussian instance/language features | **CUDA** | No | days | Excellent, but needs source images and poses we lack |
| MaskClustering / Open3DIS / OpenMask3D / SAI3D | 2D masks → 3D instances | **CUDA** (detectron2, pytorch3d) | No | 1 day+ | Strong on ScanNet; borrow the merge idea |
| Mask3D / OneFormer3D / PTv3 / Sonata | supervised or self-supervised 3D | **CUDA** | No | 1 day+ | Trained on indoor rooms; no industrial classes |
| SAM 3D Objects (Meta, Nov 2025) | single-image → 3D mesh of one object | **GPU** | No practical path | n/a | A stretch slide for the hero object only |
| gsplat / gsplat-mps / OpenSplat / Brush | true splat renders | gsplat = CUDA; gsplat-mps experimental; Brush (Rust/wgpu) runs on macOS | partial | 1–3 h | Better-looking views; no ID buffer out of the box |
| **Own numpy z-buffer renderer** (recommended) | RGB + **gaussian-ID buffer** + depth | No | Pure numpy | 1–2 h | Noisier than splats, but exact 2D↔3D correspondence |

---

## 3. Recipe

### 3.1 Environment

```bash
brew install libusb            # open3d 0.20 wheel links /opt/homebrew/opt/libusb
uv venv -p 3.12 && source .venv/bin/activate
uv pip install numpy open3d scikit-learn pyransac3d plyfile pillow \
               torch torchvision transformers open_clip_torch
export PYTORCH_ENABLE_MPS_FALLBACK=1   # for SAM 3 / ops MPS lacks
```

Tested here: torch 2.15 reports `mps.is_available() == True`, scikit-learn 1.9.1 has `HDBSCAN`, pyRANSAC-3D imports. Open3D needs libusb.

### 3.2 Tier-0 parameters (scene units; the room is ≈ 8.6 × 4.4 × 2.6)

| Step | Call | Starting value | Tune by |
|---|---|---|---|
| Downsample | `voxel_down_sample` | 0.02 | 0.03 if slow |
| Outliers | `remove_statistical_outlier` | nb=20, std=2.0 | Look at floaters |
| Normals | `estimate_normals(KDTreeSearchParamHybrid)` | r=0.05, max_nn=30 | |
| Planes | `segment_plane` loop, max 8 | dist=0.02, ransac_n=3, iters=2000 | Keep if inliers > 3 % of points and extent > 1.5 |
| Plane class | normal · (0,1,0) | > 0.95 → floor/ceiling; < 0.1 → wall | |
| Cylinders | `pyrsc.Cylinder().fit(pts, thresh=0.015, maxIteration=1000)` loop on a 30 k subsample, re-score on all points | radius 0.02–0.4; axial length > 0.4; inliers > 300 | Stop after 15 misses in a row |
| Pipe runs | 1D gaps along the axis > 0.10 split a cylinder | | |
| DBSCAN | `cluster_dbscan(eps, min_points)` | eps=0.05, min_points=20 | Plot cluster-size histogram |
| Re-split big | `HDBSCAN(min_cluster_size=50)` on `[xyz, 0.3*rgb]` | if OBB volume > 1.5 or extent > 2.5 | |
| Keep | min points / extent | ≥ 40 pts, max extent ≥ 0.05 | Recall first: keep small ones |

### 3.3 Gravity-aligned OBB

```python
def obb_yup(p):                     # p: (N,3), y is up
    c = p.mean(0)
    xz = p[:, [0, 2]] - c[[0, 2]]
    w, v = np.linalg.eigh(np.cov(xz.T)); a = v[:, 1]       # main footprint axis
    yaw = np.arctan2(a[1], a[0])
    R = np.array([[np.cos(yaw), 0, -np.sin(yaw)], [0, 1, 0], [np.sin(yaw), 0, np.cos(yaw)]])
    q = (p - c) @ R                  # local frame
    lo, hi = np.percentile(q, 2, 0), np.percentile(q, 98, 0)   # robust to floaters
    center = c + R @ ((lo + hi) / 2)
    return center, R, hi - lo        # three.js: Box3 + quaternion from R
```

Use the 2nd/98th percentile, not min/max: gaussian floaters otherwise blow up boxes.

### 3.4 Shape heuristics for a first label

| Rule (OBB extents sorted e1 ≥ e2 ≥ e3, cylinder fit if any) | Label |
|---|---|
| Cylinder, vertical axis, radius > 0.3, height > 1.2 | `boiler / vessel` |
| Cylinder, radius < 0.15, length > 5 × diameter | `pipe` |
| Cylinder, horizontal, radius 0.1–0.3, length < 1.2, near floor | `pump / motor` |
| Box-like (fill ratio > 0.6), e1 > 1.0, touching a wall | `cabinet / panel` |
| Thin, vertical, e1 > 1.5, e3 < 0.15, repeated rungs | `ladder` |
| Small (e1 < 0.3), attached to a pipe cluster | `valve / fitting` |
| Small, flat disc, on a pipe or wall | `gauge` |
| Anything else | `equipment (unlabelled)` |

These are cheap and wrong often. The curator fixes them; CLIP/VLM overwrites them in tier 1.

### 3.5 Tier-1 renderer with an ID buffer (core of the lift)

```python
def render(P, rgb, scale, K, Rcw, tcw, W=1024, H=768):
    X = P @ Rcw.T + tcw                       # world → camera, z forward
    z = X[:, 2]; ok = z > 0.1
    u = (K[0,0]*X[:,0]/z + K[0,2]).astype(int); v = (K[1,1]*X[:,1]/z + K[1,2]).astype(int)
    r = np.clip((K[0,0]*scale/np.maximum(z, 1e-3)).astype(int), 1, 4)  # radius from gaussian scale
    img = np.zeros((H,W,3)); ids = -np.ones((H,W), int); depth = np.full((H,W), np.inf)
    idx = np.where(ok)[0]; idx = idx[np.argsort(-z[idx])]          # far → near
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            sel = idx[(dx*dx + dy*dy) <= r[idx]**2]                 # disc stamp
            uu, vv = u[sel] + dx, v[sel] + dy
            m = (uu >= 0) & (uu < W) & (vv >= 0) & (vv < H)
            sel, uu, vv = sel[m], uu[m], vv[m]
            closer = z[sel] < depth[vv, uu]                         # keep nearest across stamps
            sel, uu, vv = sel[closer], uu[closer], vv[closer]
            img[vv, uu] = rgb[sel]; ids[vv, uu] = sel; depth[vv, uu] = z[sel]
    return img, ids, depth
```

- Sort far to near and assign with fancy indexing; the last write wins = nearest point. 500 k points × 100 views takes minutes on CPU.
- `scale` = `exp(max(scale_0..2))`. Clip the radius so huge floaters do not paint the screen.
- Fill small holes with a 3×3 max filter on the ID buffer before segmenting. The renders look better and SAM sees surfaces, not dots.
- Save `K, Rcw, tcw` per view to `views.json`. The web curator can reuse the same cameras for thumbnails.

### 3.6 Back-projection and merging

```python
for view in views:
    for m in masks[view]:                      # bool HxW
        gid = ids[view][m]; gid = gid[gid >= 0]
        if len(gid) < 30: continue
        node = add_node(view, set(np.unique(gid)), label_scores)
# edges: consensus between masks in different views
overlap = len(A & B) / min(len(A), len(B))     # > 0.5 → same object
# but skip if both masks see many shared gaussians and are disjoint in another view (MaskClustering rule)
union_find(edges) → instances; each gaussian → majority instance over views that saw it
```

- Throw away masks covering > 40 % of the image (floor, walls, background).
- Throw away instances seen in < 2 views. This kills most hallucinated masks.
- Keep one `label_scores` vector per mask (from SAM 3 prompt, OWLv2 box, or CLIP crop). Average them per instance.

### 3.7 Labelling crops

- CLIP: `open_clip` ViT-B/32 on MPS. Prompts: `"a photo of a {c} in an industrial boiler room"` for c in the class list (use xlsx classes `CONTROL_VALVE, PROCESS_PUMP, ELECTRIC_MOTOR, PRESSURE_TRANSMITTER, VIBRATION_SENSOR` + pipe, boiler, tank, cabinet, ladder, railing, gauge, duct, other).
- VLM (tier 2): `ollama pull qwen2.5vl:3b` (or an MLX build). Prompt with the crop and the class list; require JSON. Batch overnight; the curator shows `label_source: clip|vlm|heuristic`.
- Keep the crop PNG per proposal. The curator needs it anyway, and it is good proof for judges.

### 3.8 Metrics and proof for judges

| Metric | How | Why it lands |
|---|---|---|
| Proposals / approved / rejected / edited | Curator log | Shows density and honesty |
| Approval rate per tier | approved ÷ proposed, split by `tier0`, `tier1` | Shows the learned lift adds value |
| Coverage % | gaussians in approved non-structure objects ÷ non-structure gaussians | "x % of the equipment is now individual assets" |
| Per-class counts | bar chart | Maps to the brief's "boilers, pipes, valves…" |
| Pipeline time | per stage, on an M1 8 GB | "Runs offline on a laptop" |
| Small manual check | hand-count 20 objects in 5 views, report recall | One honest number beats ten vanity ones |

Show the reference-video "explode" view: every approved asset nudged outward along its centroid direction, each in its own colour. It visualises density in one shot.

---

## 4. What the reference videos show

Frames were grabbed with OpenCV into the scratchpad (demo 1: 145 frames, 2456 × 1200; demo 2: 290 frames, 1944 × 780).

- **Demo 1 ("Every object, its own asset", 89 objects).** An outdoor process plant. A scan gets "exploded": stacks, pipe runs, railings, stairs, platforms, heat exchangers and roof plates float apart, each in a distinct colour. The tagline is "select, move, simulate". Most of the 89 objects are **structural and piping parts**, not only machines. This says the judges count stairs, railings, platforms and pipe runs as assets. Our pipe peeling and structure assets play straight into it.
- **Demo 2 (indoor warehouse).** A splat of a room with a forklift, IBC totes, a workbench, pallets and pipework. Selected objects get a coloured mesh overlay plus a floating label card: `Forklift · mesh 01 · 91.2k tris`, `IBC tote · mesh 03 · 17.8k tris`, `Workbench · mesh 05 · 11.0k tris`. So "framing" means outline/mesh + name + id + a stat, not only a box. We should show the box, the label, the asset id, the point count, and the bound xlsx tag.
- Neither video shows per-object metadata beyond the label. Our xlsx binding is a step past the reference.

---

## 5. Risks and gotchas

- **One giant cluster.** Pipes and supports connect everything. Peel cylinders first, then cluster. If still merged, lower `eps` and re-split by HDBSCAN with colour.
- **Floaters and the collapsed-at-origin blob** (see 00/01). Filter before anything; use percentile OBBs.
- **Scale is unknown.** All thresholds are in scene units. If the floor-to-ceiling height comes out at ≈ 2.6, assume metres; otherwise rescale every parameter by `h/2.6`.
- **Over-segmentation inflates counts.** A pipe split into ten pieces is ten proposals. That is fine for recall, but the curator must have **merge** as well as approve/reject, or the approval rate looks bad.
- **Point renders are not photos.** SAM and detectors were trained on photos. Hole-filling and 1024-px views help. Expect weaker 2D results than on the mp4 frames [UNVERIFIED how much].
- **SAM 3 on MPS** needs patches (bf16 → fp32, Triton import, missing ops). Time-box it to 2 h; fall back to SAM 2.1 + OWLv2.
- **8 GB RAM.** SAM 3 + a 7B VLM will not fit together. Run stages one at a time, write to disk between them, and free models.
- **Open3D import fails** without `libusb` (seen here). Install it first, or use the numpy/sklearn path.
- **pyRANSAC-3D is slow** on 500 k points. Fit on 20–30 k subsamples, then score inliers on all points with a KD-tree.
- **Label vocabulary mismatch.** The xlsx only has five classes. Map free labels to them (`pump → PROCESS_PUMP`, `motor → ELECTRIC_MOTOR`, `valve → CONTROL_VALVE`, `gauge/transmitter → PRESSURE_TRANSMITTER`) and keep the rest as unbound scene assets.
- **Determinism.** Fix RANSAC seeds (`o3d.utility.random.seed(0)`, `np.random.seed(0)`) so the demo cache does not shuffle IDs between runs.
- **Licences.** gsplat-mps is AGPL; SAM 3 has its own Meta licence; Florence-2 is MIT. Note them in the tech note.

---

## 6. Sources

- Open3D PointCloud API (`cluster_dbscan`, `segment_plane`): https://www.open3d.org/docs/0.17.0/python_api/open3d.geometry.PointCloud.html
- Open3D OrientedBoundingBox (`create_from_points_minimal`): https://www.open3d.org/docs/latest/python_api/open3d.geometry.OrientedBoundingBox.html
- pyRANSAC-3D: https://github.com/leomariga/pyRANSAC-3D/wiki · https://pypi.org/project/pyransac3d/0.0.3
- scikit-learn HDBSCAN: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html
- Cut-pursuit / superpoint graph: https://www.Github.com/loicland/superpoint_graph · https://arxiv.org/pdf/1711.09869
- SAM 3 (Meta): https://ai.meta.com/research/sam3/ · https://docs.ultralytics.com/models/sam-3 · https://blog.roboflow.com/what-is-sam3/
- SAM 3 on Mac: https://huggingface.co/facebook/sam3/discussions/11 · https://gh.r-mj.com/facebookresearch/sam3/pull/400 · https://pypi.org/project/sam3-mlx/ · https://huggingface.co/mlx-community/sam3-image
- SAM 3D (Objects/Body): https://ai.meta.com/blog/sam-3d/ · https://arxiv.org/pdf/2511.16624
- SAGA: https://arxiv.org/pdf/2312.00860 · Gaussian Grouping: https://arxiv.org/html/2312.00732v1
- Gaga: https://arxiv.org/html/2404.07977v2 · OpenGaussian: https://proceedings.neurips.cc/paper_files/paper/2024/hash/21f7b745f73ce0d1f9bcea7f40b1388e-Abstract.html
- LangSplatV2 (notes LangSplat cost): https://arxiv.org/html/2507.07136v2
- MaskClustering: https://github.com/PKU-EPIC/MaskClustering · https://arxiv.org/html/2401.07745v2
- Open3DIS: https://arxiv.org/pdf/2312.10671 · OpenMask3D: https://arxiv.org/abs/2306.13631v2
- Sonata / PTv3: https://github.com/facebookresearch/sonata · https://arxiv.org/html/2503.16429v1
- Florence-2 on Mac: https://docs.voxel51.com/plugins/plugins_ecosystem/florence2.html · OWLv2: https://hf-2025.pages.dev/docs/transformers/v5.0.0rc0/model_doc/owlv2.md
- VLM boxes (Qwen2.5-VL, Qwen3-VL, Moondream): https://github.com/roboflow/supervision/pull/2015/files · Ollama qwen2.5vl: https://www.labellerr.com/blog/qwen-2-5-vl-vs-llama-3-2/
- Splat rendering without CUDA: https://github.com/pierotofy/OpenSplat · https://github.com/iffyloop/gsplat-mps · https://github.com/ArthurBrussee/brush
- Local checks (this session): open3d 0.20 import error without libusb; torch 2.15 MPS available; sklearn 1.9.1 HDBSCAN; Apple M1, 8 GB RAM.
