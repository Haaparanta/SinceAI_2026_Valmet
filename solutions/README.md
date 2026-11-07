# Solutions: 11 ways to win the Valmet challenge

Planning docs for eleven technical approaches (geometry, ML, logic, front end, performance). All are grounded in the **real** challenge brief (`Source-Data-Do-Not_change/…Challenge_Brief_FINAL_updated.docx`) and the Excel builder pack, which supersede the provisional `pm_pack/`.

## What the brief actually asks for

A runnable demonstrator that:

1. Extracts and 3D-frames **as many assets as possible** from `Industrial Boiler Room.ply` (a 3D Gaussian Splat).
2. Maps the Excel metadata onto those assets (random/procedural mapping is allowed) and picks a **faulty target device**.
3. Simulates an avatar or robot walking a **collision-free, realistic route** to the target.
4. **Highlights nearby assets** with frames + metadata while walking.
5. Triggers an **AI diagnosis + next steps** on arrival, grounded in the Excel pack.

Submission: working demo, repo + README, 5–8 slides, video ≤ 5 min, technical note.

**Scoring:** extraction density 30% · navigation + proximity 25% · AI grounding 20% · backend architecture 15% · demo clarity 10%. Backend beats UI polish.

## Data facts that shape every plan

- PLY: 1,506,136 gaussians, SH degree 3; only ~500k are valid (the rest are non-finite, far outliers or collapsed at the origin). Clean scene ≈ 8.6 × 4.4 × 2.6 units, **y is up**, floor ≈ y −0.9. Metric scale unverified. The PLY/mp4 files are gitignored and only exist in the main checkout.
- Excel (16 sheets): 30 assets in `Asset_Master` (control valves, pumps, motors, transmitters, vibration sensors…), `Current_State` with health scores and issue codes, 4,320 telemetry rows (3 days × 30 min), 1,000 alarms/events, 300 work orders, 50 historical service cases, 8 knowledge docs, a RAG index, 120 data-quality issues, and placeholder `Scene_Anchors` (explicitly meant to be remapped to the real scene).
- The `pm_pack` contracts assume **z-up**; the scan is y-up. Rotate once at load.

## The eleven approaches

| # | Plan | Type | Core idea | GPU? |
|---|---|---|---|---|
| S1 | [Classical geometric pipeline](S1_geometric_pipeline.md) | geometry | Splat → points → RANSAC + multi-scale DBSCAN → boxes, shape-rule labels | No |
| S2 | [Multi-view foundation lift](S2_multiview_foundation_lift.md) | ML | Render hundreds of views, GroundingDINO + SAM 2, vote masks back onto gaussians | **Yes** |
| S3 | [Supervoxel graph + VLM](S3_supervoxel_graph_vlm.md) | geometry + VLM | Over-segment with all gaussian attributes, graph-merge, Claude vision names each object | No |
| S4 | [Photoreal web twin + NavMesh](S4_web_navmesh_sim.md) | front end | Real splat in the browser, Recast navmesh, animated agent | No |
| S5 | [Scene graph + tool-using agent](S5_scene_graph_agent.md) | AI | 3D scene graph + Excel knowledge graph, Claude agent runs the mission with tools | No |
| S6 | [Rule engine / expert system](S6_rule_engine_expert_system.md) | **logic** | Geometry → facts → layered rules for labels, target choice and diagnosis, with a readable trace | No |
| S7 | [Constraint solving & ASP](S7_constraint_solver_asp.md) | **logic** | clingo for jointly consistent labels, CP-SAT for optimal Excel mapping and mission design | No |
| S8 | [2.5D raster CV](S8_raster_2p5d_cv.md) | classic CV | Height maps + height slices → OpenCV watershed/Hough → boxes; same rasters for navigation | No |
| S9 | [Mesh + convex decomposition](S9_mesh_convex_decomposition.md) | geometry | Marching cubes → CoACD convex parts = framed assets *and* collision bodies | No |
| S10 | [Rust real-time core](S10_rust_realtime_core.md) | performance | Whole pipeline in one Rust binary, live-tweakable in Rerun | No |
| S11 | [Probabilistic fault reasoning](S11_probabilistic_fault_reasoning.md) | **logic + probability** | Bayesian network / fault tree per asset class; posterior + next best check | No |

What each plan needs (libraries, hardware, skills, hours) and **measured speeds** are in [REQUIREMENTS_AND_SPEED.md](REQUIREMENTS_AND_SPEED.md). Short version: the whole geometric core (load → clean → voxel → cluster → grid → route) ran in **≈ 1.5 s in plain Python** on this Mac, so speed is not a constraint for any CPU plan. Pin Python **3.12** (`open3d` and `ortools` have no 3.15 wheels).

## Estimated score (1–5 per criterion, weighted)

| Plan | Extraction 30% | Nav 25% | AI 20% | Backend 15% | Demo 10% | **Weighted** | Build hours | Delivery risk |
|---|---|---|---|---|---|---|---|---|
| S1 | 3 | 4 | 4 | 4 | 3 | **3.60** | 10–12 | Low |
| S2 | 5 | 4 | 4 | 4 | 4 | **4.30** | 16–22 | High (GPU, time) |
| S3 | 4 | 4 | 4 | 5 | 3 | **4.05** | 14–16 | Medium |
| S4 | 3 | 5 | 4 | 3 | 5 | **3.90** | 16–20 | Medium (front-end time) |
| S5 | 3 | 4 | 5 | 5 | 3 | **3.95** | 12–14 | Medium |
| S6 | 3 | 4 | 5 | 4 | 3 | **3.80** | 10–14 | Low |
| S7 | 3 | 4 | 4 | 5 | 3 | **3.75** | +4–6 on S1 | Low–medium |
| S8 | 3 | 5 | 4 | 4 | 4 | **3.95** | 6–8 | Low |
| S9 | 4 | 5 | 4 | 4 | 4 | **4.25** | 8–10 | Medium |
| S10 | 3 | 4 | 3 | 5 | 4 | **3.65** | 14–20 | High (Rust time) |
| S11 | — | — | 5 | 4 | — | AI module only | 5–7 | Low |

These are planning guesses, not measurements. S9 reaches almost S2's score without a GPU.

## Recommendation: build in layers, not one plan

The plans share a backbone (clean → structure → boxes → Excel mapping → grid + A* → proximity → diagnosis), so they combine well:

1. **Fri night → Sat 09:00: S1 + S8 core, end to end.** Points and rasters from the same cleaned cloud; boxes, route and a cited Claude answer. Guarantees a complete demo.
2. **Sat morning: density upgrade with S9** (convex parts → many frames, consistent with collisions). If a CUDA GPU appears tonight, try **S2** instead.
3. **Sat midday: names + mapping.** Claude-vision naming from S3 on the S9 parts, then **S7 CP-SAT** for the Excel → object mapping.
4. **Sat afternoon: logic-grounded AI.** **S6** rule trace picks the target and builds the evidence chain, **S11** gives cause probabilities, Claude only narrates. Run the mission as a simple state machine (walk → scan nearby → arrive → diagnose) from S5, with cached Demo Mode replays.
5. **Only if time remains:** S4 browser visuals. Skip S10 (Python is already fast enough).

## Decisions still open

- GPU access (decides S2 vs. S9 + S3).
- Viewer: Viser (simple, Python) vs. Rerun (timeline, great for video) vs. three.js (prettiest, most work).
- Avatar type: person vs. robot (or both, as two clearance profiles).
- How "AI" the jury wants the copilot to look: pure-logic answers (S6/S11) are safest; an LLM narrator on top keeps the wow.
