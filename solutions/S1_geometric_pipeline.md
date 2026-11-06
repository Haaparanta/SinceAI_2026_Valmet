# S1: Classical Geometric Pipeline ("Splat → Points → Boxes")

**One line:** Treat the Gaussian splat as a coloured point cloud and get every asset, the floor and the route out of it with deterministic geometry only (no ML, no GPU), then show it in Viser or Rerun.

**Bet:** Robustness and speed beat sophistication. It is the safest way to have a full end-to-end demo by Saturday morning, and it is the baseline the other plans build on.

---

## Pipeline

| Stage | What we do | Libraries |
|---|---|---|
| 0. Load + clean | Read the binary PLY with `plyfile`/NumPy. Drop non-finite values, \|pos\| > 100, opacity `sigmoid(o) < 0.1`, and the gaussians collapsed at the origin. Keeps ≈ 500k of 1.5M. Colour = `0.5 + C0 · f_dc` (SH DC → RGB). | numpy, plyfile |
| 1. Axis + scale | Scene is **y-up**. Rotate to z-up once, store the transform. RANSAC the largest horizontal plane = floor (≈ y −0.9). Scale check: door height ≈ 2.0 m or the floor-to-ceiling gap; record the scale factor. | open3d (or pure numpy RANSAC) |
| 2. Structure removal | Floor (plane + 5 cm band), ceiling, and walls (large vertical RANSAC planes near the bounding hull) are labelled `structure` and removed from the object set. | open3d |
| 3. Instance extraction | Voxel-downsample (2–3 cm). **Multi-scale DBSCAN**: coarse eps finds big masses (boiler, tanks), then re-cluster each big mass with a finer eps and a height-slice split to break out pipes, valves, gauges and motors. Then merge tiny fragments by proximity + colour. | open3d / scikit-learn HDBSCAN |
| 4. 3D framing | Oriented bounding box per cluster (PCA in the floor plane + z extent). Reject boxes < 300 points or thinner than 2 cm. Expected yield: **60–150 frames**. | numpy |
| 5. Heuristic labels | Shape rules on box dims, verticality, cylinder fit, colour: `boiler`, `tank`, `pipe_run`, `valve`, `pump/motor`, `electrical_cabinet`, `gauge/sensor`, `railing`, `unknown_object`. | numpy, simple RANSAC cylinder fit |
| 6. Excel mapping | Match label → `asset_class` (CONTROL_VALVE, PROCESS_PUMP, MOTOR, …). Assign the 30 `Asset_Master` rows with Hungarian matching on class compatibility and distance to `Scene_Anchors`. Leftover frames become `context objects` (still framed, no telemetry). Pick a target with `condition_state != healthy` and the lowest `health_score`. | scipy `linear_sum_assignment`, openpyxl |
| 7. Walkable map | Floor points → 2D grid (5 cm). Any point between 0.1 m and 2.0 m above the floor = obstacle. Inflate obstacles by the agent radius (person 0.3 m, robot 0.4 m). Fill floor holes with morphological closing. | numpy, scipy.ndimage |
| 8. Path | A* from the entrance (largest free cell near the scene edge) to the free cell nearest the target box face. Smooth with a line-of-sight shortcut check, then a Catmull-Rom spline re-checked against the grid. | custom A* / `pyastar2d` |
| 9. Simulation | Step the agent at 1.2 m/s. Each tick: KD-tree query of box centres within R = 2.5 m → highlight frames, stream metadata cards. | scipy cKDTree |
| 10. AI diagnosis | On arrival: build the context from `Current_State`, the last 72 h of `Telemetry_Sample_3d`, `Alarms_Events`, `Maintenance_History`, `Historical_Service_Cases`, `Knowledge_Docs`. Claude answers with cited `doc_id`/`event_id`/`WO-` IDs. | anthropic SDK |
| 11. Viewer | **Viser** (web-based, Python-driven): splats as a point cloud, `add_box` per frame, path polyline, a moving avatar mesh, a GUI side panel for metadata + AI text. | viser |

## Build schedule (Fri 19:30 → Sun 10:00)

| When | Milestone |
|---|---|
| Fri night | Stages 0–2 + Viser showing the cleaned scene with the floor coloured |
| Sat 09:00 | Stages 3–8: boxes + A* route visible (MUST gate) |
| Sat 16:00 | Excel mapping, proximity highlighting, Claude diagnosis, cached demo answers |
| Sat night | Tune clustering for density, add labels, record a backup video |
| Sun 08:00 | Slides, README, technical note |

## Scoring estimate

| Criterion | Weight | Estimate | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Many boxes, but labels are shape guesses; clutter merges into blobs |
| Navigation + proximity | 25% | ●●●●○ | The occupancy grid + A* is explainable and collision-free |
| AI grounding | 20% | ●●●●○ | Excel is small enough to fit in one cited prompt |
| Backend architecture | 15% | ●●●●○ | Clean staged CLI, cacheable outputs |
| Demo clarity | 10% | ●●●○○ | Viser looks technical rather than cinematic |

## Risks

- **Over/under-segmentation** in dense piping: mitigate with the multi-scale split + a per-cluster max-extent rule.
- **Noisy splat floor** (holes under equipment): morphological closing + a "reachable component from entrance" check.
- **Scale unknown:** state the assumed metres-per-unit in the UI; calibrate from a door or a handrail (~1.0 m).

## Hardware

Runs on the Mac CPU. Whole pipeline < 2 min on 500k points.
