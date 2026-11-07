`// VALMET × SINCE AI 2026 · AUTOSCENE · PLAN`

# autoscene: automatic object detection and room rebuild from the splat scan

Written 2026-11-07 02:00 EET, after the research below. The manual step-by-step build (branch
`claude/equipment-room-splat-30s`) finds every part by hand-tuned geometry and a human decision per part. This is the
automatic sibling: the same source scan (`Equipment Room.ply`, 1,676,481 splats, world frame of
`orientation.py`), but the machine finds the objects, builds the room from them, and writes a textured picture of
every object it adds. Nobody has to say yes or no in the loop; the output is reviewed afterwards.

## What runs (one command, CPU/MPS on an M1 with 8 GB)

```
uv run python -m autoscene.run all          # every stage, cached per stage under out/
```

| Stage | What | How | Output |
|---|---|---|---|
| 1 `load` | real splats in the world frame | `splats.load_real_splats` (cache `data/cache/*.npy`) | in memory |
| 2 `clean` | drop reflections under the floor, floaters behind the walls / above the ceiling, lone fog | fitted floor plane, `envelope_edge` per side, kd-tree isolation test | `out/clean.npz` (keep mask) |
| 3 `structure` | floor, ceiling, 4 walls as their own objects | floor plane band, `ceiling_height_by_cells`, wall slabs at the envelope | `out/structure.npy` (label per splat) |
| 4 `views` | 197 pictures of the room with an ID buffer | **numba Gaussian-splat rasteriser** (`rasterize.py`) from a 4 × 3 grid of eye-height cameras × 8 headings × 2 pitches + 5 plan views; every pixel knows which splat made it | `out/views/NNN.png`, `out/views/NNN.ids.npz`, `views.json` |
| 5 `detect` | 2D objects in every picture | **YOLOE-26 seg** with text prompts (industrial vocabulary) + a prompt-free pass (4,585-word vocabulary) | `out/masks.npz` |
| 6 `lift` | 2D masks → 3D instances | mask pixels → splat IDs (depth-gated), greedy view-consensus merging of mask groups (`merge.py`), per-splat majority vote, nearest-neighbour fill of the splats no view saw, connectivity split | `out/instances.npz` |
| 7 `cluster` | what the detector missed | residual non-structure splats → 2 cm voxels → DBSCAN; the pipe network is split into runs by local direction (x / z / vertical / fitting), the remainder by density | `out/instances_all.npz` |
| 8 `rebuild` | the new room, one object at a time | order: floor → ceiling → walls → equipment by confidence → pipes → unlabelled; per object an SH0 PLY, the growing `room.ply`, `scene.json` with OBB + label + scores | `out/objects/*.ply`, `out/room.ply`, `out/scene.json` |
| 9 `pictures` | a picture of every added object | **Gaussian-splat render** (true colours and textures) of the object close up with the rest faint, plus the outside view of the whole room with the object highlighted, plus the best 2D detection crop as proof | `out/images/NNNN_<time>_<object>_*.png`, contact sheet, flipbook |

## Research (2026-11-07, internet)

- **No PLY-only learned 3D segmenter is usable here.** Gaussian-native segmenters (Gaussian Grouping, SAGA, OpenSplat3D,
  Fusion3DGS 2026) need the training images with poses; 3D instance networks (Mask3D, SpaCeFormer ICML 2026, Open3DIS,
  SAI3D) need CUDA and are trained on ScanNet-style rooms. A Feb 2026 industrial-scan dataset paper reports that current
  3D foundation models "do not perform well on industrial data" and that its authors went 2D-first (Grounding DINO +
  SAM, masks projected onto the point cloud). We do the same, which the challenge brief also suggests ("SAM/CLIP on
  multiple views lifted to 3D").
- **2D model choice: YOLOE-26 (Ultralytics ≥ 8.4).** Open-vocabulary detection *and* masks from one network, text
  prompts set once (`set_classes`), prompt-free mode with a 4,585-name vocabulary for discovery, runs on CPU at reduced
  resolution (docs), weights ~30 MB. SAM 3 would give better masks but its official code is CUDA-only (MPS crashes); the
  MLX port needs Python 3.13 and gated weights. YOLO-World has no masks. So: YOLOE now, SAM 3 as a later upgrade.
- **Lifting:** the ID-buffer trick (our renderer already writes depth; adding the winning splat index per pixel is a
  few lines) replaces ray casting. Cross-view merging follows MaskClustering's view-consensus idea: link two masks when
  their splat sets overlap, union-find, majority vote per splat, drop instances seen in < 2 views.
- **Sources:** Ultralytics YOLOE docs (docs.ultralytics.com/models/yoloe), arXiv 2602.15584 (industrial dataset),
  SpaCeFormer (nvlabs.github.io/SpaCeFormer), OpenMask3D, MV3DIS 2604.08916, SAM 3 local-run guides, mlx-community/sam3-image.

## Decisions taken without asking

- **Render for detection = the splat render, made fast.** The first plan was the point render with EDL (1.5 s per
  view) because the numpy splat render cost 45–155 s per view. A test on one view settled it: YOLOE found 12 objects
  (pipes, gauge, extinguisher, boxes) in the splat picture and nothing usable in the dotty point picture. So the
  splat renderer was rewritten as a compiled numba loop with early termination (`rasterize.py`): 0.6–3.4 s per
  1024 × 640 view, same maths. Point rendering survives only in the "room from outside" pictures.
- **Greedy consensus merging, not union-find.** Union-find chained three ladders and a cage into one 96,000-splat
  "step ladder" through masks that covered two of them. Groups now merge one pair at a time and every merge is
  re-checked against the views that see both (MaskClustering's view consensus); a 2D unit test pins the behaviour.
- **Pipes by local direction.** The ceiling pipe network came out as one 512,000-splat cluster; a per-voxel PCA on a
  4 cm grid (12 cm neighbourhood, majority-smoothed) splits it into x-runs, z-runs, verticals and fittings: 99 pipes,
  76 vertical pipes, 34 fittings.
- **Structure first, by geometry.** Floor, ceiling and walls are found by density, excluded from detection masks
  (so a "floor" mask never becomes an object and object masks never swallow the floor), and written as objects of
  their own because the challenge counts them and the navigation layer needs them.
- **Recall over precision.** Every lifted instance with ≥ 2 views and ≥ 150 splats is kept (pieces ≥ 250 after the
  connectivity split); the geometric fallback keeps clusters ≥ 300 splats. Labels carry their score; "unidentified
  object" is an honest label.
- **Output contract** is the same shape as the manual build (SH0 PLY per part, index space = source rows), so the
  web viewer and the metadata binder of the other branch can read it.

## Result (2026-11-07 03:05)

425 objects from 1,550,507 kept splats: 6 structure, 114 from the detector (step ladders, roll cages, barrels,
chairs, insulated pipes, tool boxes, pressure vessels, trolleys, buckets, a washing machine, a pump, an electric
motor, a control cabinet, a radiator, a fan, an exit sign …), 305 from geometry (99 pipe runs, 76 vertical pipes,
34 fittings, 76 unidentified). 93 % of the kept splats belong to an object. Numbers and limits in `README.md`.

## Not in scope here

Metadata binding, navigation, the copilot and the web viewer: those stay on the other branch and read `scene.json`.
