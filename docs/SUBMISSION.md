# Submission form · Since AI 2026 × Valmet

Copy-paste material for the hackathon submission form. Every number comes from [`video/facts.md`](../video/facts.md)
(which cites the README, `docs/build_comparison.md` and `autoscene/README.md`). The demo video is
`video/out/a2b_demo.mp4` (117 s) with captions in `video/out/a2b_demo.srt`; upload it to YouTube as public or unlisted and
paste the link in the form.

## Project name (≤ 80 characters)

**Approve-to-Build Twin**

## Tagline (≤ 140 characters)

**A plant-room scan turned into a twin of named, framed, photographed parts: 28 approved by a person, 530 found by the machine.**

## About the project (≤ 5,000 characters)

**The problem.** Field-service experts and inspection robots have to find the right equipment in complex plants,
and the context they need is split across the physical space, condition data and maintenance documents. A 3D Gaussian
Splatting scan captures a plant room photorealistically and fast, but it is blind: it does not know where the floor
is, which points are a pump, or how far the valve next to it stands.

**What we built.** Approve-to-Build Twin (`a2b`) turns the Equipment Room scan (1,676,481 Gaussian splats of a real
building-services plant room) into a twin of named, framed parts, and it does so **twice**, so the two ways can be
measured against each other:

- **The manual build.** A pipeline proposes one part at a time (floor, walls and pipes by geometry, equipment by
  probes); a person accepts or rejects each proposal; **every step photographs itself** (the proposal in green beside the
  room in its own colours, a close-up and a view from outside). Result: **28 parts** (floor, ceiling, back wall, 2 lamps,
  3 pumps, 2 control valves, a pallet jack, 17 pipes) from 35 part proposals (28 accepted, 5 rejected, 2 replaced) and
  **1,221 numbered step images**. One person with an AI agent, 23:22 → 04:31 EET, on a laptop CPU.
- **The automatic build.** No human in the loop: our own numba Gaussian-splat rasteriser renders 197 views of the room
  with an ID buffer, zero-shot **YOLOE-26** finds objects in them (1,879 masks), the masks are lifted to 3D by
  view-consensus merging, what the detector missed is clustered by geometry (the ceiling pipe network split into runs),
  a second look renders every object alone and names it. Result: **530 objects** (6 structure, 198 from the detector,
  326 from geometry), each with an oriented box, a label, a confidence and three pictures; **94 % of the kept splats**
  belong to an object. About one hour, unattended, on an 8 GB M1.
- **The viewer, live at [twinbuild.click](https://twinbuild.click).** three.js over both builds: Manual / Auto / Both,
  Scan / Model / Overlay / Wireframe, points or real Gaussian splats, 5 detail levels streamed coarse first, a build
  replay, part cards with size, position, the approval or detector pictures and the nearest parts with distances drawn
  in 3D, a measure tool, a dollhouse cut, snapshots, a phone layout, and WebXR for a Meta Quest 3 (room scale, 1 m = 1 m).
- **Measured against each other** (`make compare`): the automatic build finds **23 of the 28** human-approved parts
  (3 matched, 13 split into pieces, 7 partly found, 5 missed) and has **417 objects the manual build does not**:
  ladders, roll cages, barrels, chairs, cable trays, a control cabinet, an electric motor, a pump.

**How it is built.** Python 3.12 (NumPy, SciPy, scikit-learn, numba, PyTorch, Ultralytics YOLOE-26, pydantic) for the
offline pipelines; frozen shared contracts (pydantic + TypeScript + JSON Schema) with a drift check; a FastAPI service
that serves the exports, the step images and the comparison; a three.js + Vite + TypeScript viewer with the Spark splat
renderer and WebXR; pytest and headless-Chromium browser tests; one Docker container on Google Cloud Run, deployed by
a Cloud Build trigger on every merge to main. The heavy work runs offline on a laptop; the browser only streams and renders.

**What we met on the way.** The first scan handed out had real data only in rows 0–502,481 (the rest was random
bits), so we analysed it and moved to the newer Equipment Room scan on Friday night. There is no CUDA GPU in the team:
SAM 3 is CUDA-only, so the detector is zero-shot YOLOE on the M1's Metal GPU, and the views come from our own CPU rasteriser. Objects that
touch each other merge in the automatic build (a 3 cm re-clustering separates them again, though touching cages can still share a piece), geometry clusters are named
by shape only, and only 44 % of the splats are visible in any view. Browsers offer WebXR only on HTTPS, hence the
deployed site; GitHub Actions was unavailable, so the deploy is a native Cloud Build trigger.

**What comes next.** The approve/reject buttons in the browser (today the decision is a command), binding the brief's
Excel asset records (30 synthetic assets; the xlsx → JSON merge exists) to the parts, an occupancy grid and a
collision-free route to a faulty device, and the grounded diagnosis copilot at the target. The asset data in the brief
is synthetic and the viewer says so; the scan is real.

Repo: github.com/Haaparanta/SinceAI_2026_Valmet · Live: twinbuild.click

## Built with (comma-separated; the first five become chips)

Python, numba, YOLOE-26, three.js, Gaussian splats (Spark), FastAPI, PyTorch, NumPy, scikit-learn, pydantic, TypeScript, Vite, WebXR, Playwright, Docker, Google Cloud Run, Cloud Build, Claude Code, ElevenLabs, Remotion

## YouTube

**Title:** Approve-to-Build Twin: a scanned plant room that knows what it contains · Since AI 2026 × Valmet

**Description:**

A 3D scan of a plant room looks real, but it is blind. Approve-to-Build Twin turns the Equipment Room scan (1.7 million
Gaussian splats) into a twin of named, framed, photographed parts, twice: 28 parts approved one by one by a person, with
every decision photographed, and 530 objects found by the machine alone in about an hour on a laptop. The viewer compares
both builds: the automatic build finds 23 of the 28 approved parts and adds 417 objects the person never got to.

Live: https://twinbuild.click (desktop, phone, WebXR for Meta Quest 3)
Code: https://github.com/Haaparanta/SinceAI_2026_Valmet

0:00 The problem
0:12 One room, built twice
0:31 The live viewer
0:43 Play the automatic build
0:50 Click any object
1:04 Measure
1:08 The manual build and its approval pictures
1:24 Both builds compared
1:38 Why it matters

Built with Python, numba, YOLOE-26, three.js, Spark Gaussian splats, FastAPI, Google Cloud Run. Narration: ElevenLabs.
Since AI 2026 hackathon, Turku, Valmet track.

## Skills and tools the submission needed

- 3D Gaussian Splatting: reading PLY splats, cleaning floaters, orientation, LOD pyramids; a CPU splat rasteriser (numba).
- Computer vision: zero-shot open-vocabulary detection (YOLOE-26 with text prompts), lifting 2D masks to 3D instances by
  view consensus, geometry clustering (voxel DBSCAN, gravity-aligned oriented boxes), comparing builds by box IoU.
- Web 3D: three.js, point clouds and Spark splat rendering, streaming detail levels, WebXR (Quest 3), responsive UI.
- Backend and delivery: FastAPI, Docker, Google Cloud Run, Cloud Build triggers, custom domain, frozen contracts, tests.
- The video: screen recording of the live site (Safari, 2880 × 1800, 60 fps), a scripted cut in Remotion (React), ElevenLabs
  text-to-speech with the with-timestamps API for word-level captions (voice "Daniel"), SRT/VTT export, ffmpeg proxies.
- Writing: the problem-first narration, on-screen text for silent viewing, a facts sheet so no number is invented.
