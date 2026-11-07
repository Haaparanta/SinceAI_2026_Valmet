# Facts for the demo video and the submission text

Every number in the video, the captions and the submission text must come from this file or from the files it
cites (`README.md`, `docs/build_comparison.md`, `autoscene/README.md`, `docs/source-data/challenge-brief/README.md`).
Nothing else counts as evidence. The PM pack (`pm_pack/`) is a plan: its before/after minutes are tagged
`[HYPOTHESIS]` there and must not be quoted as results.

## The event and the brief

- Since AI 2026 hackathon, Turku, 6–8 Nov 2026. Partner track: Valmet (Valmet Automation).
- Challenge title: "Industrial Metaverse: Semantic 3D Scene Understanding & Autonomous Field-Service Copilot".
- The problem as Valmet states it: field-service staff and inspection robots have to move through complex plants,
  recognise equipment, know its condition and decide what to check next. That context is split across the physical
  space, automation and condition data, and maintenance documents. 3D Gaussian Splatting and LiDAR capture a plant
  photorealistically and fast, but the capture is semantically "blind": it does not know where the floor is, where
  the walls and obstacles are, or which points belong to which machine.
- Valmet's scoring: semantic asset extraction density & 3D framing 30 %, obstacle-aware navigation 25 %, AI
  diagnostics 20 %, backend architecture 15 %, demo clarity 10 %. "More assets is better."
- Voting format for this video: voters compare two projects at a time; the video is on every vote card; the hall is
  noisy, so many watch without sound. Submission wants a public or unlisted YouTube link, ideally under two minutes.

## Project identity

- Code name `a2b`, name **Approve-to-Build Twin**. Repo: github.com/Haaparanta/SinceAI_2026_Valmet.
- Live site: **https://twinbuild.click** (desktop, phone, and WebXR for Meta Quest 3).
- One sentence (README): making scanned industrial plants understand themselves: where equipment is, what it is, how
  to reach it, and why it needs attention.
- Source scan: `Equipment Room.ply`, **1,676,481 Gaussian splats** of a real building-services plant room (insulated
  pipes, inline pumps on vertical pipes, valves, vessels, a control cabinet, a pallet jack, roll cages, ladders,
  chairs, barrels, a sink). The asset data in the brief's Excel pack is synthetic (the viewer shows a badge
  "SYNTHETIC DATA").

## What was built: the same room, built twice

### Manual build (a person decides, part by part) — `pipeline/build.py`
- The pipeline proposes **one part at a time** (floor, walls and pipes by geometry, equipment by probes); a person
  **accepts or rejects** each proposal from the command line; **every step photographs itself** (the proposal in
  green at 80 % next to the scan in its own colours; close-up from the room plus a view from outside; failures shown
  too).
- Result: **28 parts**: floor, ceiling, back wall, 2 lamps, 3 pumps, 2 control valves, 1 pallet jack, 17 pipes.
- **447,278 of the 1,617,777 kept splats** belong to a part. 4 cleaning steps removed junk (below the floor, behind
  the wall ×2, outside the room envelope).
- Decisions: **35 part proposals (28 accepted, 5 rejected, 2 replaced) and 7 cleaning proposals**.
- Pictures: **1,221 numbered step images** (`images/0139` … `images/1359`), 1280 × 800 PNG.
- Time: **23:22 → 04:31 EET** (about 5 h), **one person with an AI agent**, on a laptop (Apple M1, 8 GB, no CUDA GPU; the manual pipeline runs on the CPU).
- State lives in `build/manifest.json`; every part keeps the indices of its splats.

### Automatic build (no human in the loop) — `autoscene/`
- Stages: clean → **197 views rendered by a numba Gaussian-splat rasteriser** (own code, CPU, ~2–3 s per 1024 × 640
  view, with an ID buffer so every pixel knows its splat) → **YOLOE-26 (zero-shot, 80 industrial text prompts)**
  finds objects in the views (1,879 masks) → masks lifted to 3D by **view-consensus merging** → what the detector
  missed is clustered by geometry (the ceiling pipe network split into runs by local direction) → a **second look**
  renders each object alone and names it → rebuild: every object gets an oriented box, a row in `scene.json` and
  three pictures (textured close-up, room-so-far from outside, detector proof).
- Result: **530 objects**: 6 structure, 198 from the detector, 326 from geometry (102 pipe runs, 73 vertical pipes,
  36 fittings, 63 unidentified objects).
- Coverage: **1,451,642 of 1,550,507 kept splats (94 %)** belong to an object.
- Time: **about one hour, unattended, on an M1 laptop** (12 min views, 1.5 min detect, 20 min relabel, 12 min pictures).
- Top labels: pipe 102, vertical pipe 73, unidentified object 63, roll cage 49, pipe fitting 36, insulated pipe 28,
  ladder 22, manifold 22, heat exchanger 17, step ladder 16, chair 11, barrel 11, cable tray 10, trolley 7,
  tool box 5, pressure vessel 5, bucket 5, workbench 5; also a washing machine, a pump, an electric motor, a control
  cabinet, a fan, an exit sign.
- Pictures: 3 per object (a sample of 72 objects is committed in `autoscene/out/samples/`), a contact sheet and a
  flipbook video of all 530.

### Manual vs automatic, measured (`docs/build_comparison.md`, `make compare`)
- The automatic build finds **23 of the 28** manual parts (82 %): 3 matched, 13 split into pieces, 7 partly found,
  5 missed (ceiling, pipe 5, control valve 1, control valve 2, pipe 14). Mean best box IoU 0.27.
- 113 automatic objects lie inside a manual part; **417 are things the manual build does not have**: ladders, roll
  cages, barrels, chairs, cable trays, a control cabinet, an electric motor, a pump.
- Honest limits (autoscene README): touching objects can merge; clusters are named by shape only; only 44 % of the
  kept splats are visible in any view; the 2D model is zero-shot, not fine-tuned.

## The web viewer (`web/`, three.js + Vite + TypeScript, no framework) — live at twinbuild.click
- **Build switch**: Manual, Auto or Both (`?scene=auto`, `?scene=both`). Manual | Auto buttons narrow the list.
- Views **Scan / Model / Overlay / Wireframe**; styles **True colour / Red-grey / By origin** (manual cyan,
  automatic amber); **Cutaway** (dollhouse), **Boxes**, **Nearby** (distance lines to the nearest parts),
  **Measure** (between two scan points), **Snapshot** (reproducible capture page), **Reset**.
- **Points | Splats**: the scan as dots or as real Gaussian splats (Spark renderer), both streamed in **5 detail
  levels, coarse first** (level 0 ≈ 4 % of the rows, so a complete coarse room is on screen after a small fraction
  of the download; the splat levels are about 52 MB in total).
- **Build replay**: the parts appear one by one in build order while the camera orbits.
- **Part card**: select a part (list, click or tap): size, position, acceptance step, the **approval images**, the
  **nearest parts with distances** drawn as leader lines in 3D; in Both, the other build's view of the same thing.
- **Both builds compared** in the panel: matched / split / partly found / missed counts with filters and badges.
- **Phones**: compact bar, bottom sheet, touch orbit and pinch.
- **Meta Quest 3**: *Enter VR* (WebXR): you stand on the floor at real-world scale (room-scale, 1 m = 1 m), walk,
  teleport, point at a part to see its name. Say "built for Meta Quest 3 through WebXR"; do not claim headset
  test results and never propose a staged VR clip. Metric scale is still unverified (1 u ≈ 1.15 m assumed).

## Backend, deployment, engineering
- `api/main.py` (FastAPI): health, demo mode, scene points/stats, both viewer exports with detail levels, the step
  images, the comparison. One Docker container on **Google Cloud Run** (europe-north1) serves API + built viewer +
  exports; a **Cloud Build trigger deploys every merge to main**; custom domain twinbuild.click.
- Frozen shared contracts (pydantic + TypeScript + JSON Schema) with a drift check; pytest suite; browser tests in
  headless Chromium; `make check` before every hand-off.
- The heavy work (cleaning, detection, rendering, export) runs **offline on an 8 GB M1 laptop with no CUDA GPU**:
  the rasteriser and the manual build on the CPU, YOLOE on the M1's Metal GPU (MPS; `autoscene/out/run_views_detect.log`
  says "loaded on mps"); the browser only streams and renders.

## What is NOT built (never show or claim it)
- No browser approve/reject buttons yet (approval is a CLI command), no `scene_graph.json`, no binding of the Excel
  assets to parts (only the xlsx → JSON dump with 30 merged asset records), no occupancy grid or route, no avatar
  walk, no AI diagnosis / copilot. These are the "what comes next".

## What we met on the way (for "about the project")
- The first scan handed out (`Industrial Boiler Room.ply`) had real data only in rows 0–502,481; the rest was
  random bits. We analysed it (`analysis/ply_study/`) and switched to the newer `Equipment Room.ply` on 2026-11-06.
- No CUDA GPU: SAM 3 is CUDA-only, so the detector is zero-shot YOLOE on the M1's Metal GPU (MPS); our own numba
  rasteriser renders the views on the CPU; everything runs on an 8 GB M1.
- Browsers only offer WebXR on HTTPS, hence the deployed site; GitHub Actions was unavailable (billing), so the
  deploy is a native Cloud Build trigger.

## Built with (candidates; the first five become chips on the vote card)
Python 3.12, NumPy, SciPy, scikit-learn, numba, PyTorch, Ultralytics YOLOE-26, MobileCLIP2, pydantic, FastAPI, uv,
three.js, Spark (Gaussian splats), WebXR, TypeScript, Vite, Playwright, Docker, Google Cloud Run, Cloud Build,
Claude Code (AI agent pair), ElevenLabs (narration), Remotion (video).

## Assets available for the video (all in the repo unless noted)
- `docs/media/manual_build.mp4` (100 s, 776 of the step images at 8 fps: every proposal, view, accept and reject),
  `docs/media/manual_build.gif` (28 frames, one per accepted part).
- `docs/media/auto_build.mp4` (62 s: close-up, room so far, detector proof per sampled object, then the finished
  room), `docs/media/auto_build.gif`.
- `autoscene/out/samples/flipbook.mp4` (all 530 objects, one frame each), `contact_sheet.jpg`, 188 sample JPGs
  (`*_a` textured close-up with box, `*_b` room so far, `*_c` detector proof), `1591_*_all_objects_textured.jpg`
  (finished room with 530 boxes), `1590_*_all_objects_coloured.jpg` (every object its own colour).
- `images/0139` … `images/1359` step PNGs: e.g. `0139` the raw scan at start, `0143`–`0147` the first cleaning
  step, `1024` Pump 2 proposed in green beside the scan (ACCEPTED), `1359` the finished twin cut open (dollhouse).
- The screen recording of https://twinbuild.click (Safari, 2880 × 1800, 60 fps, 6:25; cropped to 16:9 and cut to under two minutes).
- Theme: the project's "Cyberpunk v2 / Night City" dark look (`design/cyberpunk-tokens.css`): near-black blue
  background (#0b0d14), cyan primary, magenta accent, amber for the automatic build, cyan for the manual build;
  monospace captions in the step images.
