# S9: Mesh + Convex Decomposition ("One Geometry for Frames and Collisions")

**Type:** geometry processing · **GPU:** no · **LLM:** optional · **Runtime:** meshing ~10–30 s, decomposition ~1–3 min (cache once)

**One line:** Convert the cleaned splat into a watertight occupancy mesh, split it into near-convex parts (CoACD / V-HACD, the tool game engines use for collision shapes), and use each part both as a framed asset *and* as a collision body for navigation.

**Bet:** Convex decomposition produces many meaningful parts automatically (a pump body, its motor, a valve, a pipe segment), so density is high. The same parts are exactly what physics engines and navmesh builders want, so extraction and navigation are consistent: the avatar can never walk through something that is framed.

---

## Pipeline

| Stage | What we do | Tools |
|---|---|---|
| 1. Occupancy volume | Clean points (z-up) → 3 cm voxel grid → close small holes (3D morphological closing). | numpy, scipy.ndimage |
| 2. Mesh | Marching cubes → simplify to ~50–100k triangles. Remove the floor/wall planes found by RANSAC first so they do not dominate. | scikit-image, trimesh |
| 3. Connected parts | Split the mesh into connected components (separate machines). | trimesh |
| 4. Convex decomposition | **CoACD** per component (concavity threshold ≈ 0.05–0.1). Each convex part → OBB. Merge parts that are tiny or have nearly identical axes. Expected yield: **100–300** parts; group them into assets with a parent/child hierarchy (machine → parts). | `coacd` |
| 5. Labels | Shape rules per part (cylinder vs. box vs. elongated) and per parent; optional Claude naming from crops (S3). | |
| 6. Navigation | Floor polygon minus inflated part footprints → navmesh (Recast via `recast-navigation` in the browser, or a 2D grid + A* in Python). Collision checks against the convex parts are exact and cheap. | |
| 7. Export | Optional **glTF/USD** with one node per asset (Builder Question Q-09: portable to Omniverse/Unity/Unreal). | trimesh |
| 8. Rest | Excel mapping, proximity, Claude, viewer as S1/S4. | |

## What it needs

- 1 person for geometry; the rest as S1.
- Libraries: numpy, scipy, scikit-image, trimesh, coacd. Python 3.12.
- Time: ≈ 8–10 h; decomposition parameters need a couple of tuning runs (cache the output).

## Scoring estimate

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●●○ | Many parts with a hierarchy; parts ≠ named assets though |
| Navigation + proximity | 25% | ●●●●● | Collision geometry is the extraction itself; perfectly consistent |
| AI grounding | 20% | ●●●●○ | As S1 |
| Backend architecture | 15% | ●●●●○ | Standard, engine-ready outputs (glTF/USD) |
| Demo clarity | 10% | ●●●●○ | Coloured convex parts look striking |

## Risks

- A noisy splat gives a lumpy mesh: voxel closing + simplification first; floaters must be filtered before meshing.
- CoACD can be slow on large components: cap the triangle count per component and run it in a background job overnight, then cache.
- Too many tiny parts look like noise: merge below a size threshold and show only the parent box until the avatar is close.
