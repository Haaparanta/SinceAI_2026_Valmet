`// VALMET × SINCE AI 2026 · RESEARCH · 01`

# 01: Loading, cleaning and converting the boiler-room splat

The PLY is a standard 3DGS file, with one difference: the rotation fields are stored in a different byte order. A NumPy-only loader plus four cheap filters (finite values, bounding box, origin blob, opacity) and one KD-tree statistical-outlier pass turns 1.5 M gaussians into about 400 k clean ones in a few seconds on the laptop. From that we write a gaussian-centre point cloud for clustering and navigation, and a SOG or `.splat` file for three.js. Mesh-from-splat methods (SuGaR, 2DGS, GOF) need CUDA, and they also need the training images and camera poses, which we do not have. They are out of scope.

`2026-11-06 · measured on the real file with uv + Python 3.12 + numpy/scipy/open3d 0.19 · scripts in session scratchpad`

---

## Recommendation

Build `01_clean` as one Python script (`uv`, Python 3.12, `numpy` + `scipy`, with `open3d==0.19.0` as an optional extra). It produces four outputs:

1. **`clean_gaussians.npz`**: all 59 float fields for the kept gaussians, plus the boolean mask, so later stages can always trace back to the original gaussian indices.
2. **`points.ply`**: centres + RGB (from SH DC) + opacity + max scale. This is the input to clustering (`03_propose`) and to the floor and occupancy grid (`02_floor_grid`).
3. **`room.sog`** (preferred) or **`room.splat`** (fallback) for the browser. Make it with `npx @playcanvas/splat-transform` from a cleaned **DC-only** PLY. Keep it to ≤ 400 k gaussians and about 5–15 MB.
4. **`points_web.bin`**: decimated centres + RGB as a plain points layer for the grey/red snapshot mode (a voxel of about 2 cm gives about 140 k points, ≈ 2 MB).

Do **not** try surface extraction from the splat. If a mesh is needed for collision or framing, run Poisson or alpha-shape meshing per object on the centre points with Open3D on the CPU, or simply use oriented bounding boxes (OBBs).

Work in **scene units** with **y-up**, and keep the axes as they are. The floor is already level to within 0.7°. For metric scale, use one scalar `METRES_PER_UNIT`, held as an unverified constant until a door or a known object is measured (see Recipe §5).

### Measured on the real file (2026-11-06)

| Check | Result |
|---|---|
| Records | 1,506,136 × 59 float32, header ends at `end_header\n`, binary little-endian |
| **Field order** | `x y z scale_0..2` **`rot_1 rot_2 rot_3 rot_0`** `f_dc_0..2 opacity f_rest_0..44`. Rotation is *not* in INRIA order, so always index by name |
| Non-finite xyz / scale / opacity | 0.76 % / 0.76 % / 0.25 % of rows; `f_rest` non-finite in 10.2 % of rows (ignore it or drop SH) |
| Within ±100 units | only 41 % |
| Collapsed near origin (‖p‖ < 5 cm) | 7.4 % |
| Room box (finite, not origin) | x −5.1…4.2, y −1.9…1.5, z −5.3…0.45 |
| Kept in box at opacity > 0.005 / 0.02 / 0.05 / 0.1 | **502 k** / 467 k / 399 k / 300 k |
| Max linear scale in box, median / p90 | 0.014 / 0.054 units; a tail of huge or `inf` scales exists, so clamp it |
| SOR (k = 16, 2σ, scipy cKDTree, 287 k pts) | keeps 97 %, **0.3 s**; median nearest-neighbour spacing 0.008 units |
| Floor slab (y ≈ −0.91) PCA normal | (−0.005, 0.99993, −0.011) → **tilt 0.7°** |
| Ceiling slab (y ≈ 1.06) PCA normal | tilt 0.3° |
| Floor → ceiling-slab distance | **≈ 1.97 units** |
| Horizontal principal axis | about 6.5° off the z axis (yaw). Optional: rotate so the walls line up with the grid |
| open3d 0.20.0 (latest, cp312 arm64 wheel) | **import fails**: needs Homebrew `libusb` dylib |
| open3d 0.19.0 | imports fine; voxel 2 cm 278 k → 138 k in 0.08 s |

---

## Options compared

### A. What geometry to derive

| Option | What it gives | Cost on Mac (no CUDA) | Use it for |
|---|---|---|---|
| **Centres only** (filtered) | ~400 k pts, one per gaussian, with colour | seconds | clustering, floor/occupancy grid, OBBs. **Default** |
| Centres + **covariance sampling** (n pts per gaussian from N(μ, RΣRᵀ), clipped at 1–2σ) | denser, fills big flat gaussians on walls and floor | seconds–minute (numpy) | densify floor and walls for the occupancy grid; avoid it for small parts |
| Opacity-weighted voxel occupancy (splat each gaussian into a 5 cm grid by α) | solid/empty voxels | ~1 min numpy | navigation grid (see 03); same idea as splat-transform `--filter-floaters` |
| Poisson / BPA mesh from centres (Open3D) | rough mesh | minutes per region | optional per-object mesh in `04_mesh` |
| SuGaR / 2DGS / GOF / PGSR surface extraction | good meshes | **not feasible**: CUDA kernels, *and* they re-train from posed images, which we lack | skip it and say so in the technical note |

### B. Floater and outlier filters (applied in this order)

| Filter | Parameter | Effect here | Notes |
|---|---|---|---|
| Finite values | `isfinite` on cols 0–13 | −0.8 % | same as splat-transform `-N` |
| Bounding box | box above (or p1–p99 ± 0.3) | −55 % | the biggest win; same as splat-transform `-B` |
| Origin blob | ‖p‖ > 0.05 | −7 % | an exporter artefact [UNVERIFIED cause] |
| Opacity | σ(logit) > 0.05 | to ~400 k | 0.005 keeps 502 k. Use a low threshold for the web, higher for geometry |
| Scale clamp | max exp(scale) < 0.5 units | removes a few k | large blobs smear the clusters |
| SOR | k = 16–20, std ratio 2.0 | −3 % | scipy cKDTree or Open3D `remove_statistical_outlier(20, 2.0)` |
| Radius outlier | ≥ 4 neighbours within 0.05 | similar to SOR | Open3D `remove_radius_outlier` |
| Voxel-floater (splat-transform `-F`) | size 0.05, op 0.1, min 0.004 | keeps only gaussians that touch solid voxels | needs GPU via WebGPU, or `-g cpu` (5–10× slower) |
| Connected cluster (`-C`) | seed position | keeps only the main room | needs GPU voxelisation |

### C. Tools

| Tool | Role for us | Mac/CPU? |
|---|---|---|
| **PlayCanvas splat-transform** (npm CLI) | reads PLY/SPZ/splat/ksplat; filters (`-N -B -V -H -F`); writes **SOG**, compressed PLY, SPZ, GLB, CSV, an HTML viewer | yes (Node). WebGPU for SOG; `-g cpu` fallback |
| **SuperSplat** (browser editor) | manual crop, lasso-delete floaters, export | yes, in the browser |
| **plyfile** / raw `np.fromfile` | read/write PLY in Python | yes. `np.fromfile` is fastest |
| **gsply** (PyPI) | read/write PLY, compressed PLY, SOG, SPZ in Python | [UNVERIFIED on arm64] |
| `spz` (PyPI, Niantic lib bindings) | PLY ↔ SPZ | [UNVERIFIED on arm64] |
| antimatter15 `convert.py` | PLY → `.splat` (32 B/gaussian) | yes, pure numpy; easy to reimplement |
| gsplat / nerfstudio / INRIA 3DGS | training and rendering | CUDA. Not needed: we already have the trained splat |

### D. Web formats

| Format | Bytes / gaussian | 400 k gaussians ≈ | SH | Readers |
|---|---|---|---|---|
| INRIA PLY (SH3) | 236 | 94 MB | full | everything; too big |
| PLY DC-only | 56–62 | 24 MB | DC | Spark, splat-transform |
| `.splat` (antimatter15) | **32** | **13 MB** | DC only | Spark, GaussianSplats3D, splat-transform (read) |
| `.ksplat` (GaussianSplats3D) | ~16–32 by level [UNVERIFIED] | ~8–13 MB | optional | GaussianSplats3D, Spark |
| compressed PLY (PlayCanvas) | ~16 (chunked quantisation) [UNVERIFIED] | ~6 MB | optional | PlayCanvas, Spark |
| `.spz` (Niantic) | ~10× smaller than PLY | ~9 MB with SH, less without | yes | Spark, splat-transform |
| **SOG** (PlayCanvas, WebP textures) | ~15–20× smaller than PLY | **~5–8 MB** | yes | PlayCanvas, Spark (recent versions) |

Size targets: **laptop ≤ 1 M gaussians / ≤ 30 MB** is comfortable. **Quest 3: aim ≤ 300–500 k gaussians, SH degree 0, ≤ 15 MB** [UNVERIFIED: there is no published Quest budget; test early with Spark]. Ship the file in the repo or in a local cache, because Wi-Fi may be off during the demo.

---

## Recipe

### 1. Load (NumPy only, ~1 s for 355 MB)

```python
import numpy as np
SH_C0 = 0.28209479177387814
def load_ply(path):
    head = open(path, "rb").read(20000)
    hl = head.index(b"end_header\n") + len(b"end_header\n")
    names = [l.split()[-1].decode() for l in head[:hl].split(b"\n") if l.startswith(b"property")]
    a = np.fromfile(path, dtype="<f4", offset=hl).reshape(-1, len(names))
    col = {n: i for i, n in enumerate(names)}
    return a, col, names
a, col, names = load_ply(PLY)
xyz   = a[:, [col["x"], col["y"], col["z"]]]
scale = np.exp(a[:, [col[f"scale_{i}"] for i in range(3)]])        # log -> linear
quat  = a[:, [col["rot_0"], col["rot_1"], col["rot_2"], col["rot_3"]]]  # w,x,y,z BY NAME
quat /= np.linalg.norm(quat, axis=1, keepdims=True)
alpha = 1 / (1 + np.exp(-a[:, col["opacity"]]))                    # logit -> [0,1]
rgb   = np.clip(0.5 + SH_C0 * a[:, [col[f"f_dc_{i}"] for i in range(3)]], 0, 1)
```

This only assumes the header has float properties. Check it: `assert all(l.split()[1] == b"float" ...)`.

### 2. Clean (target ≈ 400 k)

```python
with np.errstate(all="ignore"):
    keep  = np.isfinite(a[:, :14]).all(1)
    keep &= (xyz > [-5.1, -1.9, -5.3]).all(1) & (xyz < [4.2, 1.5, 0.45]).all(1)
    keep &= np.linalg.norm(xyz, axis=1) > 0.05          # origin blob
    keep &= alpha > 0.05                                # 0.005 for web, 0.1-0.3 for geometry
    keep &= scale.max(1) < 0.5                          # giant blobs
from scipy.spatial import cKDTree
idx = np.flatnonzero(keep)
d, _ = cKDTree(xyz[idx]).query(xyz[idx], k=17, workers=-1)
md = d[:, 1:].mean(1)
keep[idx[md > md.mean() + 2.0 * md.std()]] = False      # SOR
np.savez_compressed("clean_gaussians.npz", data=a[keep], mask=keep, names=names)
```

Recompute the box from percentiles (p1–p99 of the opacity-filtered centres, ± 0.3) rather than trusting hard-coded numbers if the file changes.

### 3. Dense surface points (optional, for floor and wall occupancy)

```python
from scipy.spatial.transform import Rotation as R
Rm = R.from_quat(quat[keep][:, [1, 2, 3, 0]]).as_matrix()   # scipy wants x,y,z,w
n = 4                                                         # samples per gaussian
eps = np.clip(np.random.randn(keep.sum(), n, 3), -2, 2)       # clip at 2 sigma
pts = xyz[keep][:, None] + np.einsum("gij,gnj->gni", Rm, eps * scale[keep][:, None])
```

Only sample gaussians with α > 0.3. Use it for the occupancy grid, not for object clustering, because it blurs the edges.

### 4. Browser file

```bash
# write a DC-only PLY of kept gaussians first (drop f_rest_*; keep INRIA names)
npx @playcanvas/splat-transform clean_dc.ply -H 0 room.sog      # or -g cpu if no WebGPU
# fallback: numpy .splat writer (antimatter15 layout, 32 B):
#   pos f32x3 | exp(scale) f32x3 | RGBA u8x4 (A=sigmoid) | quat u8x4 = clip(q*128+128)
#   sort by -(prod(scale) * alpha)  (largest, most opaque first)
```

The `.splat` quaternion order is (w, x, y, z) taken from `rot_0..3` by name [verify visually in the viewer].

### 5. Up axis, gravity, metric scale

- **Up axis.** y is up (measured). The floor normal is 0.7° off +y. If needed, align it: fit a plane with RANSAC (`open3d segment_plane(0.02, 3, 1000)`) on the lowest 10 % of y, then rotate the normal to +y. This is optional at this tilt.
- **Floor height.** Take the histogram peak at the bottom of y (measured **−0.91**). It feeds `02_floor_grid`.
- **Metric scale (unverified).** Floor to ceiling-slab is **1.97 units**. Real boiler rooms are usually 3–6 m high, so 1 unit is probably **1.5–3 m**, not 1 m [UNVERIFIED]. Calibrate with one of these:
  - a door: measure the floor-to-lintel height in the points and assume **2.0–2.1 m** (EN/ISO door leaves are usually 2.0–2.1 m);
  - a handrail at **1.0–1.1 m** (common machinery-guarding rule);
  - pipe outside diameters (DN50 = 60.3 mm, DN100 = 114.3 mm, DN150 = 168.3 mm): fit a cylinder radius on one straight pipe.
  - Store `METRES_PER_UNIT` in one config file, and show "scene units" in the UI until it is set.
- **Yaw.** The main walls are about 6.5° off the axes. Rotate about y so the walls line up with the nav grid (fewer stair-step walls in the occupancy grid).

### 6. Environment

```bash
uv init --python 3.12 && uv add numpy scipy plyfile "open3d==0.19.0"
# open3d 0.20.0 has a cp312 arm64 wheel but fails to import without `brew install libusb`
```

---

## Risks & gotchas

- **Rotation byte order.** The header lists `rot_1 rot_2 rot_3 rot_0`. Code that reads columns by position (assuming INRIA order) gets the wrong quaternions. Read by name everywhere, including any third-party converter. Whether `rot_0` is really *w* for this "EGS" exporter is [UNVERIFIED]; check visually that thin pipes render as thin.
- **NaN/Inf and overflow.** `exp(scale)` and `exp(-opacity)` overflow on garbage rows. Filter for finite values first, or wrap the maths in `np.errstate`. `f_rest` has non-finite values in 10 % of rows, so drop SH (`-H 0`) for the web.
- **Two thresholds, two products.** A web splat looks better with a *low* opacity cut (0.005), which keeps soft background. Geometry wants a *high* cut (0.1–0.3). Keep both masks.
- **Centres ≠ surface.** Large flat gaussians put one centre in the middle of a wall patch. Floors can look sparse, so use covariance sampling or opacity-weighted voxels for the occupancy grid.
- **Scale assumptions leak.** Every metric threshold (robot radius 0.3 m, proximity 2 m) must go through `METRES_PER_UNIT`. If we leave it at 1.0, the robot is about 2× too large for the room.
- **open3d 0.20 import error** on a clean Mac (missing `libusb`). Pin 0.19.0, or make open3d optional and use scipy.
- **splat-transform SOG on CPU** is 5–10× slower. Fine for 400 k gaussians, but run it once in `07_demo_cache`, not live.
- **Quest 3 budget is a guess.** Test the actual file on the headset on day 1. If the frame rate drops, decimate to 200 k (splat-transform supports percentage decimation) or switch to the points layer.
- **Do not write into `Source-Data-Do-Not_change/`.** Read it with `np.fromfile` and write outputs to `data/derived/`.

---

## Sources

- PlayCanvas PLY format notes: https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/ply/
- PlayCanvas SOG format: https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/
- SOG 20× compression post: https://blog.playcanvas.com/playcanvas-adopts-sogs-for-20x-3dgs-compression
- SOG open-source announcement: https://blog.playcanvas.com/playcanvas-open-sources-sog-format-for-gaussian-splatting/
- SuperSplat streaming / LOD (≥ 1 M gaussians → streamed SOG): https://developer.playcanvas.com/user-manual/supersplat/streaming.md
- splat-transform CLI (formats, `-N -V -H -B -S -F -C`, `-g cpu`): https://github.com/playcanvas/splat-transform
- antimatter15 splat viewer and `convert.py` (32-byte `.splat`): https://github.com/antimatter15/splat, https://raw.githubusercontent.com/antimatter15/splat/main/convert.py
- ply2splat (sigmoid/exp/SH_C0 conventions): https://docs.rs/crate/ply2splat/latest/source/src/lib.rs
- Apple RealityKit splat docs (`rot_0..3` = w, x, y, z): https://developer.apple.com/documentation/visionos/rendering-gaussian-splats-with-realitykit.md
- Open3D Gaussian splatting tutorial: https://www.open3d.org/docs/latest/tutorial/visualization/gaussian_splatting.html
- Kaolin PLY loader (activation defaults): https://kaolin.readthedocs.io/en/latest/modules/kaolin.io.ply.html
- open3d on PyPI (0.20.0, cp312 macOS arm64 wheel): https://pypi.org/project/open3d/
- Niantic SPZ: https://github.com/nianticlabs/spz, https://www.nianticspatial.com/blog/spz4
- gsply (Python PLY/SOG/SPZ IO): https://pypi.org/project/gsply/0.4.4/
- Spark (three.js splat renderer, formats, WebXR): https://github.com/sparkjsdev/spark, https://sparkjs.dev/docs/overview/
- SOR parameters used on splat-derived clouds (k = 20, 2.0σ): https://arxiv.org/pdf/2503.20168
- PointNuker (GS-safe SOR/radius cleaning): https://radiancefields.com/dymensium-releases-pointnuker
- SuGaR (CUDA 11.8 requirement): https://github.com/Anttwo/SuGaR
- 2DGS (custom CUDA kernels): https://arxiv.org/pdf/2403.17888
- Gaussian Opacity Fields: https://arxiv.org/pdf/2404.10772.pdf
