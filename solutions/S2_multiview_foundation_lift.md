# S2: Multi-View Foundation Models Lifted to 3D ("Render → SAM → Vote")

**One line:** Render the splat from hundreds of virtual cameras, run open-vocabulary 2D detection + segmentation on each image, and back-project the masks onto the gaussians to get dense, *named* 3D instances.

**Bet:** The 30% density criterion and the reference videos ("every object, its own asset") reward many correctly *labelled* objects. 2D foundation models are far better at that than 3D geometry, so we borrow their eyes.

---

## Pipeline

| Stage | What we do | Libraries |
|---|---|---|
| 0. Clean | Same filtering as S1 (keep ≈ 500k valid gaussians). Rotate y-up → z-up. | numpy, plyfile |
| 1. Camera rig | Place virtual cameras on a walkable-height grid (1.6 m eye height, every 0.75 m on the floor) × 8 yaw angles + a few top-down/oblique views. ≈ 300–600 views at 1024². | numpy |
| 2. Render | Rasterise the real gaussians (RGB + depth + **per-pixel gaussian ID** of the dominant contributor). | `gsplat` (CUDA) or **Brush** (Rust/wgpu, runs on Apple Metal); fallback: a NumPy/three.js point splatter with a z-buffer |
| 3. 2D detection | **Grounding DINO / OWLv2** with an industrial prompt list (boiler, pipe, valve, pump, motor, gauge, tank, cabinet, ladder, railing, fire extinguisher, duct, panel, sensor). Then **SAM 2** turns boxes into masks. Alternative: SAM 2 "everything" + CLIP labelling of each mask. | transformers, sam2, open_clip |
| 4. Lift to 3D | For each mask, collect the gaussian IDs in the mask (depth-consistent only). Each gaussian accumulates votes `(instance_hash, label, score)`. | numpy |
| 5. Merge across views | Build a graph: two 2D masks link if their gaussian sets overlap (IoU > 0.3). Connected components = 3D instances (the "MaskClustering"/"SAI3D" idea). Majority vote on the label; confidence = vote share. | networkx / union-find |
| 6. 3D framing | OBB per instance after statistical outlier removal. Expected yield: **100–250 labelled frames**, including small items (gauges, valves, signs). | open3d |
| 7. Excel mapping | Labels match Excel `asset_class` directly (valve → CONTROL_VALVE, pump → PROCESS_PUMP …). Hungarian assignment as in S1. | scipy |
| 8. Navigation | Re-use S1 (occupancy grid + A*). The rendered depth maps give a bonus: free-space carving makes the floor map cleaner. | numpy |
| 9–10. Simulation + AI | Same as S1. Add: on arrival, also send the best rendered view of the target to Claude vision ("does the visual state agree with the telemetry?"). | anthropic SDK |
| 11. Viewer | Viser, or a three.js web viewer with a real splat renderer (Spark / `@mkkellogg/gaussian-splats-3d`) so the scene looks photoreal. | viser / three.js |

## Build schedule

| When | Milestone |
|---|---|
| Fri night | Get a GPU (cloud A10/L4 or a team member's PC). Render 10 test views and check they look right |
| Sat 09:00 | Full render sweep + GroundingDINO/SAM 2 batch run; S1-style navigation done in parallel by a second person |
| Sat 16:00 | Lifting + cross-view merging produce 3D instances; mapping + viewer integration |
| Sat night | Tune the prompt list and merge thresholds; precompute everything into `scene_assets.json` |
| Sun 08:00 | Slides with a "views → masks → 3D" figure (judges love this) |

## Scoring estimate

| Criterion | Weight | Estimate | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●●● | Most frames *and* real semantic names; closest to the reference videos |
| Navigation + proximity | 25% | ●●●●○ | Same as S1, slightly cleaner floor |
| AI grounding | 20% | ●●●●○ | Plus visual cross-check |
| Backend architecture | 15% | ●●●●○ | Impressive, but more moving parts |
| Demo clarity | 10% | ●●●●○ | Named objects read clearly on screen |

## Risks

- **No CUDA on the Mac.** Highest risk. Mitigation: book a cloud GPU tonight; Brush (Metal) as a plan B; worst case render with a simple point splatter (lower quality masks).
- **Splat render quality:** a third of the file is garbage; floaters could fool SAM. Filter by opacity/scale first and render only the clean subset.
- **Time:** model downloads + batch inference ≈ 1–2 h of GPU time. Cache every intermediate.
- **Mis-merges** across views: keep a depth-consistency check before voting.

## Hardware

Needs a CUDA GPU (≥ 16 GB) for a few hours, or accept slower Metal/CPU inference.
