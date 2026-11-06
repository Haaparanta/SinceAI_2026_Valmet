`// VALMET × SINCE AI 2026 · RESEARCH · 03`

# 03: Collision-free navigation and proximity highlighting

Build a 2D occupancy grid from the cleaned splat offline in Python (floor from a height histogram, obstacles from a height band, holes closed, unknown kept separate from free). Plan with clearance-weighted A* over a Euclidean distance transform, smooth the path, and ship it as JSON. In three.js, play it back on a `CatmullRomCurve3` at constant speed, use the same grid for first-person collision, and drive proximity highlighting from a per-frame radius query with hysteresis.

`2026-11-06 · CRITERION c2 (25 %) · SANITY-CHECKED ON THE REAL SCAN`

---

## Recommendation

1. **Grid, not NavMesh, as the source of truth.** A 2D grid at 5 cm cells is 172 × 96 for our room. Every step (EDT, A*, smoothing) runs in about 1 ms in Python. The grid is also easy to *show* to the judges as an image, which a NavMesh is not.
2. **Planner: `skimage.graph.route_through_array`** (8-connected, geometric costs) on a cost map `1 + k·exp(-(clearance − r)/σ)`. This gives "walk down the middle of the aisle" behaviour for free. Then string-pull (line-of-sight shortcutting, the Theta* idea) and resample with Catmull-Rom.
3. **Bake everything offline** into `route.json` + `occupancy.png` + `clearance.png`. The browser only replays. This matches non-negotiable 3 (offline, Wi-Fi off).
4. **Browser:** avatar follows `CatmullRomCurve3.getPointAt(u)`; first-person mode uses `PointerLockControls` plus a lookup into the same grid (slide along walls). Quest 3: teleport onto walkable cells only.
5. **Proximity:** asset centres in a tiny array (≤ 30–100 assets) → brute-force distance per frame is enough. Enter at 1.5 m, leave at 2.0 m (hysteresis), optional raycast line-of-sight against the asset boxes.
6. **Stretch only:** recast-navigation-js NavMesh in the browser, for a "second opinion" overlay or click-to-go in walk mode.

---

## What the real scan says (measured 2026-11-06, read-only)

Filters used: finite, |xyz| < 100, not at origin, opacity > 0.3, then p1–p99 box. Result: **506,651 gaussians**.

| Measure | Value |
|---|---|
| Height (y) histogram, 5 cm bins | Strong floor peak at **y ≈ −0.93…−0.88**; ceiling peak at **y ≈ +1.05**; ~6 % of points *below* the floor (−1.48…−1.03) = noise / reflections |
| Grid at 5 cm, x × z | **172 × 96 cells** (8.6 × 4.8 units) |
| Cells with floor points (\|h\| < 6 cm) | 28 % raw, much more after closing |
| Obstacle band 0.30–1.60 above floor, ≥ 8 pts/cell, binary opening | 12 % of cells |
| Free after `binary_closing(floor, 4)` minus obstacles | 46 %; **largest connected component 44 %** |
| Walkable after agent radius 0.25 | 26 % (0.15 → 34 %) |
| `distance_transform_edt` / `route_through_array` | **< 1 ms / ~1 ms** |

Takeaways. The floor is easy to find. Raw floor coverage is sparse, so hole filling is mandatory. A low obstacle threshold (≥ 3 points) shatters the free space into ~150 islands; floaters must be removed with a count threshold plus morphological opening. Scale is still [UNVERIFIED]: if a unit is not a metre, scale the agent radius accordingly (check a door or a pump against its xlsx bbox).

---

## Options compared

### Map representation

| Option | Fits our data? | Effort | Notes |
|---|---|---|---|
| **2D occupancy grid (x–z), height band** | Yes: single floor level, 8.6 × 4.4 room | Low | Obstacle = anything in the band between "knee" and "head" height. Easy to dilate, EDT, render as PNG. |
| 2.5D height map (max/min y per cell) | Partly | Low–med | Lets you allow steps/curbs and detect overhangs (pipes above head). Useful as a *second* layer for the "pipes overhead are OK" story. |
| 3D voxel grid | Overkill | Med | Needed only for multi-level or crawling under pipes. 172 × 52 × 96 ≈ 0.86 M voxels is fine in numpy, but nothing to gain for a walking avatar. |
| NavMesh (Recast) | Needs a clean triangle mesh | Med–high | Splat → mesh is noisy; holes in the floor become holes in the navmesh. Best as a browser-side extra. |

### Planners

| Planner | Path quality | Speed on 172 × 96 | Verdict |
|---|---|---|---|
| **A* / Dijkstra on clearance cost** (`skimage.graph`, `pyastar2d`) | Optimal on grid; zig-zag 45° steps | ~1 ms | **Use.** Clearance cost gives aisle-centre routes. |
| Theta* / Lazy Theta* (any-angle) | Shorter, straight segments | ms in pure Python [UNVERIFIED] | Get the same effect with A* + line-of-sight string pulling. |
| JPS | Same as A* on uniform grids | Faster | Does not support weighted costs well; skip. |
| D* Lite | Same as A*, incremental replans | — | Only if obstacles change live (they do not). |
| RRT / RRT* | Random, jittery, needs smoothing | Slower | Looks *less* realistic; name-drop only. |
| Visibility graph | Shortest, hugs corners | Fast with few polygons | Hugs walls: wrong look for "realistic". |
| Recast/Detour (`computePath`) | Funnel-smoothed, corner-hugging unless radius set | Fast (WASM) | Stretch in browser. |

### Python libraries

| Library | Use | Note |
|---|---|---|
| `scipy.ndimage` | `binary_closing/opening`, `label`, `distance_transform_edt` | All we need for the map. EDT `sampling=` handles non-square cells. |
| `scikit-image` | `graph.route_through_array` / `MCP_Geometric`, `draw.line` for LOS | `fully_connected=True` allows diagonals; `geometric=True` weights diagonals by √2. |
| `pyastar2d` | C++ A* with numpy float32 weights | Weights must be ≥ 1 for a valid heuristic. |
| `pathfinding` (brean) | Pure-Python A*, Dijkstra, etc. | Fine for demos; weighted support [UNVERIFIED]. |
| `networkx` | `astar_path` on a grid graph | Works but slow to build; unnecessary. |
| Recast in Python | No official bindings; `pyRecast`/`PyRecastDetour` are unofficial and immature | Avoid offline Recast. |

---

## Recipe

### Parameters (scene units, assume ≈ metres [UNVERIFIED])

| Name | Value | Why |
|---|---|---|
| `cs` cell size | 0.05 | 172 × 96 grid; fine enough for 60 cm aisles. |
| floor | mode of y-histogram in lower half (≈ −0.90) | RANSAC plane (Open3D `segment_plane`) as a cross-check if the floor is tilted. |
| floor band | \|y − floor\| < 0.06 | Points that *are* floor. |
| obstacle band | 0.30 … 1.60 above floor | Above ankle-height clutter and noise; below overhead pipes. Lower bound 0.15 makes the map much noisier. |
| obstacle threshold | ≥ 8 gaussians per cell, then `binary_opening` | Kills floaters. |
| floor closing | `binary_closing(iterations=4)` (= 20 cm holes) | Fills sparse floor. |
| agent radius `r` | 0.25 (human), 0.20 (robot) | Dilation by EDT threshold. |
| clearance cost | `1 + 4·exp(-(d − r)/0.3)` | Pushes path to aisle centre. |

### Unknown vs free

Three states, not two: **free** (floor seen, no obstacle), **occupied** (obstacle band dense), **unknown** (nothing seen). Closing the floor turns small unknown holes into free. Large unknown areas stay *non-walkable* (safe default), but render them in a third colour so the judge sees we know the difference. Outside the largest connected component = unreachable.

### Offline code sketch (`06_route.py`)

```python
import numpy as np, json
from scipy import ndimage as ndi
from skimage.graph import route_through_array
from skimage.draw import line

CS, R = 0.05, 0.25
# xyz: cleaned gaussian centres (N,3), y-up, from 01_clean
h, e = np.histogram(xyz[:,1], bins=60)
floor_y = e[np.argmax(h[:30])] + (e[1]-e[0])/2          # lower-half peak
lo = xyz[:, [0,2]].min(0)
ij = ((xyz[:, [0,2]] - lo) / CS).astype(int)
W, H = ij.max(0) + 1
hgt = xyz[:,1] - floor_y

def count(mask):
    g = np.zeros((W, H), np.int32); np.add.at(g, tuple(ij[mask].T), 1); return g

floor = ndi.binary_closing(count(np.abs(hgt) < 0.06) >= 1, iterations=4)
occ   = ndi.binary_opening(count((hgt > 0.30) & (hgt < 1.60)) >= 8)
# optional: burn in approved asset bboxes from the curator as hard obstacles
free  = floor & ~occ
lab, _ = ndi.label(free); sizes = np.bincount(lab.ravel()); sizes[0] = 0
free &= lab == sizes.argmax()                            # one reachable region
clear = ndi.distance_transform_edt(~occ) * CS            # metres to nearest obstacle
walk  = free & (clear > R)
cost  = np.where(walk, 1 + 4*np.exp(-(clear - R)/0.3), np.inf)
cost[~walk] = 1e9                                        # skimage needs finite; or use MCP mask

def snap(p):                                             # nearest walkable cell to a world xz point
    c = ((np.array(p) - lo) / CS).astype(int)
    idx = np.argwhere(walk); return tuple(idx[np.argmin(((idx - c)**2).sum(1))])

start, goal = snap(spawn_xz), snap(target_front_xz)      # goal = point in front of P-005, not its centre
cells, total = route_through_array(cost, start, goal, fully_connected=True, geometric=True)

def los(a, b):                                           # string pulling (Theta*-style)
    rr, cc = line(*a, *b); return walk[rr, cc].all() and clear[rr, cc].min() > R + 0.1

pulled = [cells[0]]; k = 0
while k < len(cells) - 1:
    j = len(cells) - 1
    while j > k + 1 and not los(cells[k], cells[j]): j -= 1
    pulled.append(cells[j]); k = j

pts = [(lo[0] + (i+.5)*CS, floor_y, lo[1] + (j+.5)*CS) for i, j in pulled]
json.dump({"floor_y": float(floor_y), "cell": CS, "origin": lo.tolist(), "shape": [int(W), int(H)],
           "path": pts, "length_m": float(sum(np.linalg.norm(np.diff(np.array(pts), axis=0), axis=1))),
           "min_clearance": float(min(clear[c] for c in cells))}, open("route.json", "w"))
# also save walk/occ/unknown as occupancy.png and clear as clearance.png (same origin + cs)
```

The `+0.1` margin in `los` stops string pulling from undoing the aisle-centre preference. Alternative smoothing: Chaikin corner cutting (2–3 rounds) before Catmull-Rom; re-check each smoothed sample against `walk`.

### Browser playback (three.js)

```ts
const curve = new THREE.CatmullRomCurve3(route.path.map(p => new THREE.Vector3(...p)), false, 'centripetal');
const len = curve.getLength(); let s = 0; const speed = 1.2;    // m/s, walking pace
function tick(dt: number) {
  s = Math.min(s + speed * dt, len);
  const u = s / len;                                  // getPointAt is arc-length parametrised
  avatar.position.copy(curve.getPointAt(u));
  const t = curve.getTangentAt(u); avatar.rotation.y = Math.atan2(t.x, t.z);
  mixer.update(dt);                                   // 'Walking' clip; switch to 'Idle' at goal
}
```

Use `'centripetal'` to avoid overshoot loops through obstacles. Avatar: three.js example **RobotExpressive.glb** (fits the "robot" story, has Idle/Walking/Running clips) or **Soldier.glb**; licences are reported MIT/CC0 by third parties [UNVERIFIED], so check the three.js repo notes before shipping. Mixamo characters are free to use but need an Adobe account login to download [UNVERIFIED]. Clone animated models with `SkeletonUtils.clone`.

**First-person walk with collision.** `PointerLockControls` + WASD. Each frame: propose `next = pos + v·dt`; look up the cell in the `walk` bitmap (load `occupancy.png` into a `Uint8Array`); if blocked, try x-only then z-only (wall sliding). Keep eye height at `floor_y + 1.6`. No physics engine needed. For mesh-accurate collision instead, three-mesh-bvh's "Player movement" example does capsule vs BVH.

**Quest 3 (WebXR).** No stick-walking (motion sickness, harder). Use teleport: controller ray hits the floor plane, accept only if the cell is walkable, then move the rig via `XRReferenceSpace.getOffsetReferenceSpace`. Also offer "ride along" on the avatar path. Sean Bradley's `teleportvr` is an option but old (2018).

### Proximity highlighting

```ts
const ENTER = 1.5, EXIT = 2.0;                       // hysteresis band, metres
for (const a of assets) {                            // ≤ 100 assets: brute force is < 0.1 ms
  const d = Math.hypot(a.cx - p.x, a.cz - p.z);      // horizontal distance; or box-to-point distance
  if (!a.near && d < ENTER && hasLOS(p, a)) a.near = true, show(a);
  else if (a.near && d > EXIT) a.near = false, hide(a);
}
```

- Use distance to the **box surface** (`Box3.distanceToPoint`), not the centre, so big boilers trigger fairly.
- `hasLOS`: one `Raycaster` from eye to box centre against the other asset boxes (or the grid in 2D with a DDA). Skip assets behind a wall; this is what makes it "realistic".
- Add a minimum display time (e.g. 0.8 s) on top of hysteresis to kill flicker.
- KD-tree (`scipy.spatial.cKDTree`) or BVH only matters for thousands of objects or point-level queries. Pre-compute offline: for each path sample, the list of nearby asset IDs → the browser can show a timeline of "assets passed".

---

## Showing it to judges

The brief rewards spatial processing over polish, so make the processing visible.

1. **Map panel / toggle:** top-down overlay on the floor: free (dark), occupied (red), unknown (hatched grey), inflated margin (orange), clearance heatmap, path in cyan.
2. **Numbers on screen:** path length (m), ETA at 1.2 m/s, min clearance along path, planning time (ms), cells, % of floor reconstructed vs hole-filled.
3. **Before/after strip:** raw A* zig-zag vs string-pulled vs clearance-weighted. One image says "we thought about realism".
4. **Proof of no collisions:** offline assert `walk[cell]` for every resampled point; print "0 collisions in 400 samples" in the HUD.
5. **Proximity log:** side list "passed: M-006 (1.2 m), P-002 (0.9 m)…" with frames popping on in the 3D view.
6. **Replan button:** pick another target from the curator list → new route in ~ms (pre-baked for all 30 assets keeps it offline).

---

## Risks & gotchas

- **Floaters become walls.** Count threshold + opening, and clip the obstacle band above ankle height. Measured: threshold 3 → ~150 disconnected islands.
- **Holes become walls or voids.** Close the floor; keep large unknown regions non-walkable but visible.
- **Target inside an obstacle.** The faulty pump is occupied by definition. Goal = nearest walkable cell on the side facing the room (`snap` + max clearance), and orient the avatar to face the asset.
- **Start in a small island.** Restrict start/goal to the largest connected component.
- **Axis mix-ups.** PLY is y-up; grid is x–z; PNG rows are often z flipped. Store `origin`, `cell`, and axis order in `route.json` and render one debug overlay early.
- **Unverified scale.** All metre values assume 1 unit ≈ 1 m. Check one asset size against the xlsx bbox before tuning radii.
- **Smoothing cuts corners.** Re-validate every Catmull-Rom sample against the grid; use centripetal parametrisation.
- **Doors and narrow gaps** may close entirely after dilation by 0.25; drop to 0.20 (robot) if the target becomes unreachable, and say so on screen.
- **Recast in-browser** needs a clean, triangulated, counter-clockwise mesh; noisy splat meshes give fragmented navmeshes. Do not depend on it.
- **Quest performance:** heavy splat rendering plus per-frame raycasts can drop frames; precompute proximity per path sample.

---

## Sources

- Theta* (Daniel, Nash, Koenig, Felner, JAIR 2010): https://arxiv.org/abs/1401.3843 · https://jair.org/index.php/jair/article/view/10676
- Lazy Theta* in 3D: https://ojs.aaai.org/index.php/AAAI/article/view/7566
- scipy `distance_transform_edt`: https://docs.scipy.org/doc/scipy-1.6.3/reference/generated/scipy.ndimage.distance_transform_edt.html
- scikit-image `route_through_array` / `MCP_Geometric`: https://github.com/scikit-image/scikit-image/blob/v0.19.2/skimage/graph/mcp.py
- Distance-transform planner (Corke robotics toolbox): https://petercorke.github.io/robotics-toolbox-python/_modules/roboticstoolbox/mobile/DistanceTransformPlanner.html
- pyastar2d: https://pypi.org/project/pyastar2d
- python-pathfinding: https://pypi.tcis.de/data/web/json/pathfinding
- recast-navigation-js (MIT; `computePath`, `exportNavMesh`): https://github.com/isaac-mason/recast-navigation-js
- @recast-navigation/three (`threeToSoloNavMesh`, `NavMeshHelper`): https://cdn.jsdelivr.net/npm/@recast-navigation/three@0.43.1/README.md
- Generator options: https://recast-navigation-js.isaacmason.com/docs/modules/generators.html
- Recast: no official language bindings: https://recastnav.com/md_Docs__2_BuildingAndIntegrating.html
- pyRecast (unofficial): https://sourceforge.net/p/pyrecast/wiki/
- three-mesh-bvh (MIT) and player-movement demo: https://github.com/gkjohnson/three-mesh-bvh · https://gkjohnson.github.io/three-mesh-bvh/characterMovement.html
- PointsBVH: https://gkjohnson.github.io/tools/docs/three-mesh-bvh/PointsBVH.md
- three.js example models (RobotExpressive, Soldier), licence second-hand: https://skillselion.com/skills/opusgamelabs/game-creator/game-3d-assets
- WebXR teleport discussion (offset reference space): https://discourse.threejs.org/t/teleport-functionality-in-webxrmanager-webxrcontroller/18605
- WebXR teleportation sample: https://immersive-web.github.io/webxr-samples/teleportation.html
- TeleportVR: https://sbcode.net/threejs/teleportvr
- Measured data: scratchpad scripts `nav_check.py`, `nav2.py` on `Industrial Boiler Room (1).ply` (read-only), 2026-11-06.
