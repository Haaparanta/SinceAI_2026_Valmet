# S3: Supervoxel Graph + VLM Labelling ("Over-segment, Merge, Ask Claude")

**One line:** Over-segment the cleaned splat into thousands of small supervoxels using every gaussian attribute (position, colour, normal, scale, opacity), merge them into objects with a graph cut, then crop-render each object and let a vision-language model name it.

**Bet:** Gaussians carry more than XYZ: their colour, anisotropic scale and orientation tell surfaces apart. Using all 59 properties gives better boundaries than plain DBSCAN, and using a VLM *only for naming* (not for segmenting) avoids S2's GPU dependency.

---

## Pipeline

| Stage | What we do | Libraries |
|---|---|---|
| 0. Clean + features | Same filter as S1. Per gaussian: position, RGB (SH DC), view-dependent colour strength (SH rest norm), principal axis from the quaternion + scales → normal, flatness, elongation. | numpy |
| 1. Structure | Floor / walls / ceiling by RANSAC as in S1, kept as `structure` instances (they also count as framed scene elements). | open3d |
| 2. Supervoxels | VCCS-style supervoxels (≈ 5–8 cm seeds) or a k-NN graph + Felzenszwalb segmentation on a combined distance `‖Δp‖ + α‖Δrgb‖ + β(1 − n·n')`. ≈ 5–20k segments. | open3d kNN, scikit-learn, custom union-find |
| 3. Graph merge | Region adjacency graph. Merge edges by a learned-free score: convexity (concave boundary = object border), colour similarity, normal continuity. Stop when segments hit a size/shape prior. Pipes: grow elongated segments along their principal axis. | networkx |
| 4. 3D framing | OBB per merged object. Expected yield: **80–200 frames**. | numpy |
| 5. VLM naming | For each object: render 3 crops (front, side, context) with a simple point splatter, plus box dims in metres. Send a batch to **Claude vision**: "Label this industrial object; choose from [list] or 'other: …'; give a confidence and a one-line description." Cache all answers to JSON. 150 objects ≈ 150 small calls, fine for the budget. | anthropic SDK, a NumPy/Pillow point renderer |
| 6. Excel mapping | Label → `asset_class`; Hungarian assignment. Unmapped objects keep their VLM description as metadata. | scipy |
| 7–10. Navigation, simulation, AI, viewer | Same as S1 (grid + A*, KD-tree proximity, Claude diagnosis, Viser). | — |

## Build schedule

| When | Milestone |
|---|---|
| Fri night | Feature extraction + S1-style structure removal + Viser |
| Sat 09:00 | Supervoxels + merge producing boxes; navigation done in parallel |
| Sat 16:00 | Crop renderer + Claude labelling batch; mapping; proximity + diagnosis |
| Sat night | Tune merge weights against what we see; cache; backup video |
| Sun 08:00 | Slides/README |

## Scoring estimate

| Criterion | Weight | Estimate | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●●○ | Good boundaries + real names, slightly fewer small items than S2 |
| Navigation + proximity | 25% | ●●●●○ | Same as S1 |
| AI grounding | 20% | ●●●●○ | VLM descriptions enrich the context |
| Backend architecture | 15% | ●●●●● | A novel, explainable pipeline that uses splat-native features |
| Demo clarity | 10% | ●●●○○ | Viser |

## Risks

- **Merge tuning** takes iteration; budget Saturday evening for it.
- **Crop render quality** from a point splatter is lower than a real splat render; Claude may hedge. Include box size + height above the floor in the prompt.
- **API cost/latency:** batch + cache once; the demo never calls the labeller live.

## Hardware

Mac CPU + the Claude API. No GPU required.
