# S10: Rust Real-Time Core ("Process the Whole Scan Live")

**Type:** performance engineering · **GPU:** no · **LLM:** Claude over HTTP · **Runtime:** full pipeline in well under 1 s

**One line:** Write the whole spatial pipeline (PLY parse, filter, voxel, clustering, occupancy, A*, proximity queries) as one Rust binary that logs to Rerun, so the scene is reprocessed live on stage with sliders (cluster size, agent radius) and the result updates instantly.

**Bet:** The brief explicitly invites Rust and grades "backend architecture & technical implementation" (15%). A live, parameter-tweakable pipeline is a memorable demo of robustness. But Python is already fast enough here (see the speed guide), so this is a differentiation play, not a necessity.

---

## Pipeline

| Stage | Crate |
|---|---|
| PLY parse (binary, 59 floats × 1.5M, memory-mapped) | `memmap2`, `bytemuck` |
| Filter, voxel hash, statistics | `rayon` for parallel iterators |
| Spatial index | `kiddo` (k-d tree) |
| Clustering (DBSCAN on voxel centres) | own implementation over `kiddo` or `linfa-clustering` |
| RANSAC floor/walls | `nalgebra` |
| Occupancy grid + A* | `pathfinding` crate |
| Visualisation | `rerun` Rust SDK (points, boxes, path, avatar, text log) |
| AI | `reqwest` → Claude Messages API, or a tiny Python sidecar |
| Excel | `calamine` (reads .xlsx directly) |

## What it needs

- 1–2 people fluent in Rust (Cargo is installed on the Mac).
- Time: ≈ 14–20 h. Highest build effort of all plans for the same features.

## Scoring estimate

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Same algorithms as S1 |
| Navigation + proximity | 25% | ●●●●○ | As S1, but tweakable live |
| AI grounding | 20% | ●●●○○ | Less time left for the AI part |
| Backend architecture | 15% | ●●●●● | Typed, fast, single binary |
| Demo clarity | 10% | ●●●●○ | Live parameter changes impress |

## Risks

- Biggest time sink of all plans; Rust ML/geometry crates are thinner than Python's.
- Recommended only as a *port of S1's hot loop* after the Python demo works, or skip.
