# Gaussian Splats (Particle Fields), Omniverse Materials and Rendering

| | |
|---|---|
| URL | https://docs.omniverse.nvidia.com/materials-and-rendering/latest/particle-fields.html |
| Title | "Gaussian Splats (Particle Fields) — Omniverse Materials and Rendering" |
| Publisher / date | NVIDIA · © 2023–2026, page showed "Last updated on Nov 06, 2026" |
| Companion read | the converter script: https://github.com/PixarAnimationStudios/OpenUSD/blob/dev/extras/imaging/examples/hdParticleField/py3dgsPlyToUsd.py |
| Pack's design implication | Native particle-field support and PLY-to-USD workflow |
| Read | 2026-11-06, both in full |

## Part 1: the Omniverse documentation page

### Section structure

1. (intro) Particle fields
2. Importing 3D Gaussian Splats into Omniverse
3. Particle Fields and Shadows
4. Particle Fields and Color
5. Adjusting Particle Field Brightness
6. Improving Denoising in RTX – Real-Time 2.0
7. Other Particle Field Formats

### Section by section

**Intro.** *Particle fields* are a new **OpenUSD geometry type** for 3D Gaussian Splats and related radiance fields such as **3DGUT**. Omniverse RTX renders them natively, so they take part in path tracing, shadows, reflections and refraction. Known issue: **DLSS Frame Generation** can cause artifacts; turn it off if you see them.

**Importing.** Convert the PLY with the OpenUSD example script, then reference or payload the result into a stage:

```bash
python py3dgsPlyToUsd.py --input path/to/model.ply --output path/to/output.usd
```

The page provides a sample (`flowers_1.zip`, CC-BY-SA, scan by Andrii Shramko / Teleportour).

**Shadows.** Particle fields **receive** shadows from other geometry (they can look "blobby") but **don't cast** them unless the *Casts Shadows* checkbox is enabled.

**Colour.** In this release all `ParticleField` prims are treated as **display-referred sRGB** and **tonemapping is skipped**. A future version will honour `UsdColorSpaceAPI`.

**Brightness.** Scene lights don't brighten splats. Use the `emission_intensity` input of the built-in MDL material **`ParticleFieldEmissive`** (default **1.0**; < 1 dims, > 1 brightens). Unbound prims use this material by default. The page's Kit Python snippet creates a material at `/World/Looks/SplatBrightness`, points it at `ParticleFieldEmissive.mdl`, sets `emission_intensity = 0.5` and binds it with `MaterialBindingAPI`. Changing `inputs:emission_intensity` later affects every field bound to that material.

**Denoising (RTX Real-Time 2.0).** Splats use stochastic transparency, which makes depth and colour noisy. The renderer accumulates depth and albedo over several Gaussian hits along each ray; the budget is **Max Gaussians To Accumulate**, default **48**.

**Other formats.** 3DGUT training and conversion are handled by NVIDIA's **3DGRUT** project (github.com/nv-tlabs/3dgrut).

## Part 2: the converter script `py3dgsPlyToUsd.py`

Header: © 2026 Pixar. Writes a **y-up** stage with `metersPerUnit = 1.0` and one prim of type **`UsdVol.ParticleField3DGaussianSplat`**.

| PLY property | USD attribute (via `Create…Attr`) | Transform |
|---|---|---|
| `x, y, z` | `positions` | none (extent clamped to ±50,000 for the bounding box only) |
| `scale_0..2` | `scales` | `exp()` |
| `rot_0..3` | `orientations` | `Gf.Quatf(rot_0, rot_1, rot_2, rot_3)`, i.e. **`rot_0` is the real part**, then normalised |
| `opacity` | `opacities` | `sigmoid()` |
| `f_dc_0..2` | `radiance:sphericalHarmonicsCoefficients` (first vec3) | none |
| `f_rest_*` | same primvar, following coefficients | reordered from channel-major; degree detected from count: 9 → 1, 24 → 2, **45 → 3** |
| — | `radiance:sphericalHarmonicsDegree` | 0–3 from the count above |

Other details:

- Its own PLY parser handles binary little/big-endian and ASCII and looks properties up **by name**, so our file's unusual `rot_1, rot_2, rot_3, rot_0` order is handled correctly.
- Optional flags: `--generateSh` (build DC colour from `red/green/blue` columns) and `--generateScales` (isotropic scales from k-NN distances; needs SciPy).
- Quirk: an unexpected `f_rest` count sets degree 0 but still writes the partial coefficients.

**Our PLY has every field the script needs and gives SH degree 3.** It does no cleaning, so the ~80 % junk Gaussians would be converted too. Run it on a cleaned PLY.

## Glossary

| Term | Meaning |
|---|---|
| ParticleField / `ParticleField3DGaussianSplat` | OpenUSD schema (`UsdVol`) for splat-type radiance fields |
| 3DGUT | 3D Gaussian Unscented Transform, a splat variant that supports distorted cameras and secondary rays |
| MDL | NVIDIA's Material Definition Language |
| Reference / payload | USD ways to include one file in another; payloads can be loaded lazily |

## Relevance to our build

- **If we go Omniverse, this is the import path**, and each extracted asset can become its own USD prim next to the splat. The builder pack's `scene_path` values (`/SyntheticPlant/AREA-03/P-005`) are already USD-style paths, so the mapping layer fits naturally.
- **Highlighting:** binding a brighter `ParticleFieldEmissive` material to a sub-field is one way to make the faulty asset glow. Simpler: draw a box prim around it.
- **Splats aren't solid.** They don't cast shadows by default and can't be collision targets, so floor, obstacles and frames need separate mesh/box proxies, which we build anyway for pathfinding.
- **Cost/benefit:** Omniverse is heavy to set up in a 38-hour build. It's a strong "production path" slide (Builder Q-09: portability across OpenUSD/Omniverse) even if the live demo runs in a lighter Python or web viewer.
- **Decoding reference:** the script is an authoritative example of how to decode our PLY's attributes (exp scale, sigmoid opacity, w-first quaternion, channel-major SH). The [PLY doc](../../source-data/boiler-room-ply/README.md#decoding-each-attribute) follows it.
