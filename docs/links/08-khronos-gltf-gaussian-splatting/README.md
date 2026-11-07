# Khronos glTF Gaussian Splatting extension (`KHR_gaussian_splatting`)

| | |
|---|---|
| URL | https://www.khronos.org/news/press/gltf-gaussian-splatting-press-release |
| Title | "Khronos Announces glTF Gaussian Splatting Extension" |
| Publisher / date | The Khronos Group · press release, Beaverton OR, **3 February 2026** |
| Companion read | the spec README on GitHub: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting |
| Pack's design implication | Open baseline for Gaussian splats in glTF |
| Read | 2026-11-06. Press release in full; spec README about 80 % verbatim, the rest via summary |

> **Status conflict.** The February press release announces a *release candidate* with ratification expected in Q2 2026. The GitHub README now says "Complete, Ratified by the Khronos Group". The ratification date was not found. Treat it as ratified but check the README before relying on details.

## Part 1: the press release

### Section structure

1. Gaussian Splatting: Real-Time Radiance Field Rendering
2. Industry Need for Standardization
3. Seamless glTF Integration
4. Flexible, Future-Proof, and Extensible
5. Industry Support
6. Providing Feedback

### Summary

- **What:** a release candidate of `KHR_gaussian_splatting`, a baseline extension that lets glTF 2.0 store 3D Gaussian splats in a standard, cross-platform way.
- **How:** it extends the glTF **mesh primitive**. Each splat has position, orientation, scale, colour and opacity. Renderers that understand the extension draw splats; others **fall back to a point cloud**.
- **Design:** uncompressed, GPU-ready data; a base **ellipse kernel**; deliberately algorithm-agnostic so later extensions can add kernels, colour spaces, projections and sorting methods.
- **Compression:** proposed follow-on extensions are Niantic Spatial's **SPZ** and Qualcomm's **L-GSC**.
- **Alignment:** Khronos is coordinating with the **Alliance for OpenUSD (AOUSD)** so glTF and OpenUSD splat representations stay convertible (see [link 9](../09-nvidia-openusd-particle-fields/README.md)).
- **Integration:** splats can live in the same glTF as meshes, terrain and photogrammetry. Cesium says it will be a key part of **OGC 3D Tiles 2.0**.
- **Origin:** driven by Metaverse Standards Forum town halls from January 2025.
- **Contributors:** Autodesk, Bentley/Cesium, Esri, Huawei, Niantic Spatial, NVIDIA, XGRIDS. People quoted include Neil Trevett (Khronos president), Patrick Cozzi (Bentley/Cesium), Brian McClendon (Niantic Spatial CTO) and others.
- **Industrial examples shown:** an industrial facility captured by drone (5,255 images) and processed in Esri ArcGIS Reality; a power substation; a chemical refinery tileset. Digital twins and infrastructure monitoring are named target uses.

## Part 2: the specification (GitHub README)

### Extension object on the mesh primitive

| Field | Required | Values |
|---|---|---|
| `kernel` | yes | `"ellipse"` (only value defined) |
| `colorSpace` | yes | `"srgb_rec709_display"` or `"lin_rec709_display"` |
| `projection` | no | default `"perspective"` |
| `sortingMethod` | no | default `"cameraDistance"` |

The primitive's `mode` must be **POINTS (0)**; the material is ignored for splat rendering. Node transforms must decompose into translation, rotation and **positive** scale.

### Attributes

| Attribute | Type | Required | Encoding |
|---|---|---|---|
| `POSITION` | VEC3 float | yes | position |
| `KHR_gaussian_splatting:ROTATION` | VEC4 float / snorm8 / snorm16 | yes | unit quaternion, glTF order **(x, y, z, w)** |
| `KHR_gaussian_splatting:SCALE` | VEC3 float / (u)norm8 / (u)norm16 | yes | **linear** (not log), non-negative |
| `KHR_gaussian_splatting:OPACITY` | SCALAR float / unorm8 / unorm16 | yes | **linear 0–1** (sigmoid already applied) |
| `KHR_gaussian_splatting:SH_DEGREE_0_COEF_0` | VEC3 float | yes | DC colour coefficient |
| `…:SH_DEGREE_1_COEF_0..2` | VEC3 float | if degree ≥ 2 used | 3 coefficients |
| `…:SH_DEGREE_2_COEF_0..4` | VEC3 float | if degree 3 used | 5 coefficients |
| `…:SH_DEGREE_3_COEF_0..6` | VEC3 float | optional | 7 coefficients |
| `COLOR_0` | | fallback | `clip(SH0 × 0.282095 + 0.5, 0, 1)`, sRGB-decoded when colour space is sRGB |

Rules: a degree must be complete, and lower degrees must be complete before higher ones. Coefficients are packed from lowest to highest *m*.

### Rendering model

- Diffuse colour = `SH0 × 0.2820947917738781 + 0.5`; higher SH evaluated with the Condon–Shortley phase.
- Covariance Σ = M C Cᵀ Mᵀ, with M the node's 3×3 transform and C built from scale and rotation.
- Ellipse kernel cut off at 3σ; splats sorted back-to-front by camera distance and alpha-blended; negative colours clamped to 0.
- Colours are **display-referred**: scene lighting, exposure and tonemapping generally do not affect them.
- Exporters should train in glTF's coordinate system (**y-up, right-handed**), otherwise positions, quaternions and SH must be rotated on load.

## Mapping our PLY to this extension

| Our PLY | glTF attribute | Conversion |
|---|---|---|
| `x, y, z` | `POSITION` | none (scene is already y-up) |
| `rot_0` (w), `rot_1..3` (x, y, z) | `ROTATION` | **reorder to (x, y, z, w)** and normalise |
| `scale_0..2` | `SCALE` | `exp()` |
| `opacity` | `OPACITY` | `sigmoid()` |
| `f_dc_0..2` | `SH_DEGREE_0_COEF_0` | as is |
| `f_rest_0..44` | `SH_DEGREE_1..3_COEF_*` | de-interleave from channel-major (all R, then all G, then all B) into per-coefficient RGB |

*(This mapping is our reading of the spec and the OpenUSD converter; neither document states it for this exact file.)*

## Relevance to our build

- **One file for scene + semantics.** Because splats can share a glTF with meshes, our bounding boxes, path polyline and avatar could ship in the same file as the cleaned scan. A web viewer (Cesium, three.js) could then load one asset.
- **Point-cloud fallback is our cheap viewer path too.** If a splat renderer is too slow or fiddly, render the cleaned Gaussian centres as coloured points; the spec endorses that as a valid degraded view.
- **Pitch line:** Khronos (glTF) and AOUSD (OpenUSD) both standardised splats in 2026, with digital twins and infrastructure as headline uses. A splat-based plant twin is therefore a standard format, not a research toy.
- **Coordinate system:** glTF is y-up like our PLY, so no axis swap is needed for export.
