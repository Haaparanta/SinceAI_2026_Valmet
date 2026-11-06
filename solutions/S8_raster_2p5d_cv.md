# S8: 2.5D Raster Computer Vision ("Turn the Room into Images")

**Type:** classic CV · **GPU:** no · **LLM:** optional · **Runtime:** < 1 s for all rasters + detection

**One line:** Flatten the 3D scene into a stack of top-down images (height map, density per height slice, colour) and side elevations, run mature 2D image processing (OpenCV connected components, watershed, Hough circles/lines), then lift results back to 3D boxes.

**Bet:** 2D image tools are faster, better known and easier to debug than 3D ones. The room is only ≈ 8.6 × 5.1 × 2.7 m: at 2 cm per pixel a top-down image is ~430 × 250 px, tiny. Navigation is *already* a 2D raster problem, so floor, obstacles, objects and route share one representation.

---

## Pipeline

| Stage | What we do | Tools |
|---|---|---|
| 1. Rasterise | From the cleaned points (z-up): per pixel max height, min height, point count, mean colour; plus **height slices** every 20 cm (0–0.2, 0.2–0.4, … 2.6 m). Also two side elevations (XZ, YZ). | numpy `bincount`, ~50 ms |
| 2. Floor + walls | Floor = pixels whose min height ≈ floor level. Walls = long Hough lines in the max-height map along the room border. | OpenCV |
| 3. Footprints | Height map minus floor → "object height" image. Threshold > 10 cm → binary mask → distance transform + **watershed** splits touching equipment. | OpenCV, scikit-image |
| 4. Vertical split | For each footprint, look at its height-slice profile: a gap in occupancy (e.g. a valve above a pipe) splits it into stacked objects. | numpy |
| 5. Pipes & round things | Hough circles on height slices → vertical pipes/tanks; Hough lines on side elevations → horizontal pipe runs. Each becomes its own framed asset. | OpenCV |
| 6. Boxes | Footprint min-area rectangle (`cv2.minAreaRect`) × height range = oriented 3D box. Expected yield: **50–150** frames. | OpenCV |
| 7. Labels | Shape rules (S6) on footprint size, height, roundness; optional: send the top-down crop + side crop to Claude for a name (as S3). | |
| 8. Navigation | The same rasters at 5 cm: free = floor and no obstacle 0.1–2.0 m; inflate by agent radius; A* or a **distance-transform-weighted** path that prefers the corridor centre (looks much more human). | OpenCV `distanceTransform`, pyastar2d |
| 9. Debug images | Every stage writes a PNG (great for slides: "height map → footprints → boxes → route"). | |
| 10. Rest | Excel mapping, proximity, Claude diagnosis, Viser/Rerun viewer as S1. | |

## What it needs

- 1 person with OpenCV experience.
- Libraries: numpy, opencv-python, scikit-image, scipy. Python 3.12 or 3.15.
- Time: ≈ 6–8 h for extraction + navigation.

## Scoring estimate

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Good for floor equipment; overhead/stacked objects need step 4 to work |
| Navigation + proximity | 25% | ●●●●● | Corridor-centre paths look natural; very robust |
| AI grounding | 20% | ●●●●○ | As S1 |
| Backend architecture | 15% | ●●●●○ | Simple, testable; every stage visible as an image |
| Demo clarity | 10% | ●●●●○ | The raster stage images make a clear story |

## Risks

- Objects hanging above others (pipes over pumps) are hidden in a pure top-down map: the height slices and side elevations are essential, not optional.
- Watershed over-splits textured objects: tune the distance-transform threshold on the real scan tonight.
