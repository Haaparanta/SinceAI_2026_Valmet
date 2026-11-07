`// VALMET × SINCE AI 2026 · AUTOSCENE`

# autoscene: automatic object detection and room rebuild from the splat scan

One command turns `Equipment Room.ply` (1.68 M Gaussian splats) into a room of named, framed objects, each with
its own PLY and three pictures. No human in the loop; the pictures are the review material afterwards. The manual
sibling (branch `claude/equipment-room-splat-30s`) builds the same room one approved part at a time; this is the
machine's version of the same job on the same source data.

```
cd autoscene
uv sync                                   # Python 3.12, torch (CPU/MPS), ultralytics, numba, scipy, scikit-learn
ln -s "../../Source-Data-Do-Not_change" data/raw      # or put "Equipment Room.ply" in data/raw/
uv run python -m autoscene.run all        # ~35 min on an M1 with 8 GB: 12 min views, 1.5 min detect, 20 min pictures
uv run python -m autoscene.run all --from lift        # rerun from a stage (every stage caches under out/)
uv run python -m pytest -q
```

Weights (`yoloe-26s-seg.pt`, 31 MB, and the MobileCLIP2 text encoder, 242 MB) download into `weights/` on first use.

## How it works

| Stage | What | How | Output |
|---|---|---|---|
| `clean` | drop reflections under the floor, floaters past the walls and above the ceiling, lone fog | fitted floor plane, outermost dense layer per side (`wall_edge`), ceiling by plan cells, kd-tree isolation | `out/state.npz`, `scene_info.json` |
| `clean` | floor, ceiling and four walls labelled | thin slabs at those surfaces (white lamp splats stay objects) | same |
| `views` | 197 pictures of the room | **numba Gaussian-splat rasteriser** (`rasterize.py`, EWA projection, front-to-back blending, early termination, ~2–3 s per 1024 × 640 view) with an **ID buffer**: every pixel knows the splat that made it | `out/views/*.png`, `*.ids.npz` |
| `detect` | 2D objects in every picture | **YOLOE-26 seg** (Ultralytics) with 80 text prompts (industrial vocabulary); masks → splat ids, depth-gated so background seen through gaps is dropped | `out/detections.npz` (1,879 masks) |
| `lift` | 2D masks → 3D instances | greedy **view-consensus merging** (`merge.py`): two mask groups join only when the views that see both put them in one mask; per-splat majority vote; fill of the splats no view saw; connectivity split | `out/instances.npz` |
| `cluster` | what the detector missed | residual splats → voxel DBSCAN; the ceiling pipe network is split into runs by **local direction** (x / z / vertical / fitting), the rest by density | `out/instances_all.npz` |
| `rebuild` | the new room, object by object | floor → ceiling → walls → detector objects (confidence × size) → clusters; gravity-aligned OBB per object | `out/objects/*.ply`, `out/room.ply`, `out/leftovers.ply`, `out/scene.json` |
| `pictures` | three pictures per object | a) textured close-up (object opaque, rest faint and dimmed, OBB drawn), b) the room from outside with the object highlighted and the room built so far, c) the detector's best view with its box (proof); then the finished room coloured per object and textured, a contact sheet and a flipbook video | `out/images/NNNN_<time>_<object>_{a,b,c}.png`, `contact_sheet.png`, `flipbook.mp4` |

`scene.json` is the contract for the rest of the system (metadata binding, navigation, viewer): per object
`index, name, label, source (structure | yoloe | cluster), confidence, n_splats, obb {center, yaw_deg, extent, R,
corners}, aabb, scores (label → summed detector score), views, detections, ply`.

## Measured on the Equipment Room scan (2026-11-07, Apple M1, 8 GB)

| | |
|---|---|
| kept after cleaning | 1,550,507 of 1,676,481 splats (floor plane rms 1.3 cm, walls x −4.24..+4.91, z −3.77..+3.54, ceiling y +1.31) |
| views / masks | 197 views, 1,879 YOLOE masks ≥ 30 splats |
| objects | **425**: 6 structure, 114 from the detector, 305 from geometry (99 pipe runs, 76 vertical pipes, 34 fittings, 76 unidentified) |
| detector labels | step ladder 13, roll cage 16, barrel 11, chair 10, insulated pipe 13, tool box 5, pressure vessel 5, trolley 5, bucket 5, washing machine, pump, electric motor, control cabinet, radiator, fan, exit sign, … |
| coverage | 1,447,247 of 1,550,507 kept splats belong to an object (93 %), 103,260 leftovers |

## In the web viewer

`make viewer-auto` (from the repo root) writes `data/derived/viewer_auto/scene.{bin,json}` in the same layout the
manual build uses, and the three.js viewer shows it at `http://localhost:5173/?scene=auto`: the build slider replays
the 425 objects in order, Boxes draws every frame, the snapshot page takes the same parameter.

## Known limits (honest list)

- Objects that touch each other can still merge when every view that sees them masks them together (the widest
  "roll cage" is 2.7 u wide: several cages). The consensus test stops chains, not shared masks.
- The ceiling "beams" of the detector are insulated pipes; `rebuild.LABEL_ALIAS` renames them. Clusters are named
  by shape only ("pipe", "vertical pipe", "pipe fitting", "unidentified object").
- Only 44 % of the kept splats are visible in any view (the rest are inside, underneath or too faint); those are
  filled from their nearest labelled neighbour within 3 cm, three rounds.
- The 2D model is zero-shot (YOLOE text prompts, no fine-tuning). SAM 3 would give better masks but its official
  code is CUDA-only; see `PLAN.md` for the research behind the choices.

## Layout

```
autoscene/
  autoscene/            the package: scene, views, rasterize, detect2d, lift, merge, cluster, rebuild, pictures, run
  tests/                synthetic unit tests (no PLY, no model)
  data/raw -> ../../Source-Data-Do-Not_change    (symlink, gitignored)  data/cache/  (gitignored splat cache)
  out/                  every stage's output; PLY / npy / npz and the views are gitignored, images and json are kept
  weights/              model weights (gitignored)
  PLAN.md               the plan and the research it rests on
```

Reused from the manual build (same branch family): the PLY loader and world orientation (`splats.py`,
`orientation.py`, `splat_rows.py`, `ply_io.py`), the point renderer and picture composer (`render.py`) and the
height/plane finders (`geometry.py`).
