# Requirements & speed: what each plan needs, and what is fast enough

## 1. Measured on this Mac (Apple Silicon, CPU only, 2026-11-06)

Benchmark on the real `Industrial Boiler Room (1).ply` with plain numpy + scipy + scikit-learn (Python 3.15 via `uv`). One run, wall-clock per stage:

| Stage | Result | Time |
|---|---|---|
| Load binary PLY (1,506,136 × 59 floats) with `np.fromfile` | 355 MB in RAM | **0.27 s** |
| Filter (finite, \|pos\| < 100, opacity > 0.1, not at origin, 1–99 percentile box) | 300,337 points | **0.37 s** |
| Voxel downsample 3 cm | 95,077 points | **0.24 s** |
| k-d tree build | | **0.03 s** |
| 2,000 radius queries (r = 0.3 m) (≈ proximity check for a whole walk) | | **0.02 s** |
| DBSCAN (eps 6 cm, min 8) on the voxel cloud | 173 clusters (untuned) | **0.28 s** |
| Occupancy grid 5 cm + obstacle inflation | 173 × 102 cells | **0.01 s** |
| A* on that grid, pure Python | | **< 0.1 s** (grid has only 17k cells) |
| Scene extent after filtering | 8.64 × 5.07 × 2.74 units | |

**Conclusion: the whole geometric core (load → boxes → route) runs in ≈ 1.5 s in plain Python.** Speed is not a constraint for any CPU plan. The room is small: no need for Rust, C++ or a GPU to make the geometry fast. Time should go into extraction *quality* and the AI layer, not performance work.

Even an untuned DBSCAN gives 173 clusters in 0.3 s, so a density of 100+ framed objects is realistic tonight.

## 2. Time budget per run (what "fast enough" means for each step)

| Step | Budget | Why | Who fits |
|---|---|---|---|
| Offline extraction (run once, cache JSON) | < 10 min | Must be re-runnable several times on Saturday while tuning | All plans; S2 needs ~1–2 h GPU, S9 ~1–3 min |
| Load cached scene into viewer | < 5 s | Live demo start | All |
| Route computation | < 1 s | Re-plan on stage (person ↔ robot) | All (measured < 0.1 s) |
| Proximity query per frame | < 5 ms | 30 fps animation | All (measured 0.01 ms/query) |
| AI diagnosis on arrival | < 10 s live, **0 s cached** | Never wait on stage; Demo Mode replays cached answers | Claude live + cache; S6/S11 are instant and offline |
| Viewer frame rate | ≥ 30 fps | Smooth video | Viser/Rerun with ≤ 300k points; three.js splat viewer with the cleaned splat |

## 3. Environment facts (checked tonight)

| Fact | Consequence |
|---|---|
| Homebrew Python **3.15** is the default, **3.12** is also installed | **Pin the project to Python 3.12** (`uv init --python 3.12`) |
| `open3d` and `ortools` have **no Python 3.15 wheels**; they resolve on 3.12 | Needed for S1 (RANSAC helpers), S7 (CP-SAT) |
| `torch`, `viser`, `rerun-sdk` resolve on both | |
| `clingo`, `pgmpy`, `coacd`, `opencv-python`, `trimesh`, `scikit-image`, `pyastar2d`, `plyfile` resolve on 3.12 | All logic and geometry plans are installable |
| No CUDA GPU on the Mac | S2 needs a cloud GPU or a teammate's PC; everything else runs locally |
| `uv`, `node`, `cargo` available; no `ffmpeg` | Install `ffmpeg` (brew) before recording the video |
| PLY/mp4 files are gitignored and only in the main checkout | Load from an absolute path or a `DATA_DIR` env var |

## 4. What each plan needs

| Plan | Type | Key libraries | Hardware | People / skills | Build hours to full demo | Pipeline runtime | Fast enough? |
|---|---|---|---|---|---|---|---|
| S1 Geometric | geometry | numpy, scipy, sklearn, open3d, viser | Mac CPU | 1–2, Python + 3D basics | 10–12 | ~2 s | ✅ |
| S2 Multi-view lift | ML | torch, sam2, GroundingDINO/OWLv2, gsplat/Brush | **CUDA GPU ≥ 16 GB** | 2, CV/ML | 16–22 | 1–2 h GPU (once) | ⚠️ only if GPU tonight |
| S3 Supervoxel + VLM | geometry + VLM | numpy, networkx, anthropic | Mac CPU + API | 2 | 14–16 | ~10 s + ~150 cached VLM calls (~5 min once) | ✅ |
| S4 Web NavMesh | front end | three.js, Spark/gaussian-splats-3d, recast-navigation, FastAPI | Mac + browser | 2, TS + Python | 16–20 | browser real time | ✅ but costly in hours |
| S5 Scene graph agent | AI | networkx, pandas, anthropic, rerun | Mac CPU + API | 1–2 | 12–14 | agent run 20–60 s live, cached replay 0 s | ✅ with cache |
| **S6 Rule engine** | **logic** | pandas only (optional clingo) | Mac CPU | 1 | 10–14 | **< 5 s, offline** | ✅✅ |
| **S7 Constraint / ASP** | **logic** | ortools, clingo | Mac CPU | 1 (declarative modelling) | +4–6 on top of S1 | 0.1–5 s per solve | ✅✅ |
| S8 2.5D raster CV | classic CV | numpy, opencv, scikit-image | Mac CPU | 1, OpenCV | 6–8 | **< 1 s** | ✅✅ |
| S9 Convex decomposition | geometry | trimesh, scikit-image, coacd | Mac CPU | 1 | 8–10 | 1–3 min (once) | ✅ |
| S10 Rust core | performance | rayon, kiddo, pathfinding, rerun, calamine | Mac CPU | 1–2, **Rust** | 14–20 | < 1 s | ✅ but unnecessary |
| **S11 Bayesian fault reasoning** | **logic + probability** | pgmpy or hand-written, pandas | Mac CPU | 1, basic probability | 5–7 | < 10 ms per asset | ✅✅ |

## 5. Logic-based options in one view

Logic is a strong fit here because the Excel pack is structured, small and rule-shaped (issue code → interpretation → next check → doc), and the brief's own docs demand cited IDs, confidence and "never silently guess".

| Where logic helps | Plan | What it replaces | Gain |
|---|---|---|---|
| Naming clusters from shape facts | S6 (rules), S7 (ASP, jointly consistent) | ML labelling | Explainable labels, no GPU |
| Excel → object mapping | S7 (CP-SAT) | Random/greedy mapping | Optimal, constraint-respecting assignment in < 1 s |
| Choosing the faulty target | S6 rule L3 / S7 | Hard-coded target | Defensible priority (picks **P-005**, ASSET-017: criticality A, health 44, FOULING) |
| Mission design (route passes healthy assets) | S7 | Arbitrary waypoints | Better proximity demo |
| Diagnosis | S6 (rule chain), S11 (Bayesian posterior) | Free-form LLM | Zero hallucination; LLM only narrates |
| Agent behaviour | S5 + a finite-state machine (walk → scan nearby → arrive → diagnose) | Free-running agent | Deterministic on stage |

The strongest logic stack: **S8 or S1 geometry → S7 mapping/labelling → S6 rule trace + S11 probabilities → Claude as narrator.** Fully offline-capable, under 10 s end to end, and every output has an ID trail.
