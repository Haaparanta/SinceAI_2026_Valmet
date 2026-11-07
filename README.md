`// SINCE AI 2026 × VALMET`

# SinceAI_2026_Valmet

Making scanned industrial plants understand themselves: where equipment is, what it is, how to reach it, and why it needs attention.

`HACKATHON · BUILD FRI 19:30 EET · DEADLINE SUN 10:00 · STATUS: BUILD · WEDGE: APPROVE-TO-BUILD TWIN`

## Hackathon Challenge

Imagine entering a digital industrial plant where the environment does more than look real. It understands where machines are, what they are, how people or robots could move between them and which equipment needs attention. Today's 3D captures can be visually extraordinary—but they often lack the meaning needed for intelligent action.

Valmet challenges you to bridge that gap. Explore how spatial perception, semantic 3D understanding and AI-grounded equipment information could transform a scanned industrial environment into a navigable, useful digital world. Think computer vision, point-cloud intelligence, digital twins, robotics simulation and an assistant that can explain the context behind a maintenance decision.

This is a chance to make AI understand not just words and numbers, but physical space. A strong demonstration could point toward industrial operations where service experts and autonomous systems find the right equipment faster, navigate complex facilities more intelligently and turn fragmented technical data into confident, context-aware action.

## Where we are

*As of 2026-11-07 02:16 EET (step image 0964).*

- **Master scan:** `Equipment Room.ply` (1,676,481 splats, every row real), replacing `Industrial Boiler Room (1).ply` since 2026-11-06 23:15. It is gitignored like every `.ply`; see [docs/source-data](docs/source-data/README.md).
- **Step-by-step build** ([`pipeline/build.py`](pipeline/build.py)): the twin is built one proposal at a time, and a person accepts or rejects each one. So far: 4 cleaning steps (below floor, behind wall ×2, outside the room envelope) and **19 accepted parts**: floor, ceiling, back wall, 2 lamps, pump 1, pallet jack 1 and pipes 1–12. That is 396,650 of the 1,617,777 kept splats. The state is in [`build/manifest.json`](build/manifest.json), and every step has numbered images in [`images/`](images/) (0001–0964; 0001–0138 belong to two archived earlier runs).
- **Web viewer** ([`web/`](web/)): three.js view of the build (Scan / Model / Overlay / Wireframe, parts list, build replay) plus the snapshot page `capture.html`. **Points | Splats** (G) switches the scan between the dot cloud and real **Gaussian splats** ([Spark](https://sparkjs.dev)), with every view, the build replay, selection and the cutaway working on splats too ([details](#gaussian-splats)). Select a part (list, click or tap) for its **info card**: size, position, acceptance step with its **approval images**, and the **nearest parts with distances**, also drawn as leader lines in 3D. **Measure** (M) gives the distance between two scan points, **▶** (Space) replays the build part by part, and the parts list filters by name and kind. It works on desktop, on phones (compact top bar, build list as a bottom sheet, touch orbit/pinch) and in **WebXR on Meta Quest 3**: *Enter VR* puts you on open floor inside the room at real-world scale, and walking in your room walks you through the scan ([how](#vr-on-meta-quest-3)).
- **API** ([`api/main.py`](api/main.py)): scaffold only. It serves health, demo mode, scene points/stats and the viewer scene.
- **Also done:** M1 clean loader (`pipeline/01_clean.py`), the xlsx → JSON dump with 30 merged `AssetRecord`s (`pipeline/05_bind_metadata.py --dump`), frozen contracts with a drift check, and a timelapse video tool.
- **Not started yet** (planned in [`AGENTS.md`](AGENTS.md)): the browser curator with approve buttons, `data/scene_graph.json`, binding xlsx assets to parts, the occupancy grid and route, and the copilot / `Diagnosis`.

## Quick start

```bash
make setup          # Python 3.12 venv (uv), web deps (npm), data/raw -> Source-Data-Do-Not_change
make help           # every target with a one-line description
```

The `.ply` / `.mp4` files are not in git; put them in `Source-Data-Do-Not_change/` first ([how](docs/source-data/README.md#getting-the-large-files)).

| Task | Command |
|---|---|
| Show the build so far | `uv run python pipeline/build.py status` |
| Propose the next part / decide it | `uv run python pipeline/build.py part …` then `… accept` or `… reject --note TEXT` (all subcommands are listed in the [`build.py`](pipeline/build.py) docstring) |
| Look at the build in the browser | `make viewer && make web`, then open http://localhost:5173 |
| Walk the build in VR (Quest 3) | `make viewer && make web-vr`, then open `https://<laptop-ip>:5173` in Quest Browser ([details](#vr-on-meta-quest-3)) |
| Scripted screenshots | `make snap Q="src=overlay&part=pipe_3"` (needs `make web` running) |
| Timelapse of the step images | `make timelapse` → `docs/timelapse.mp4` (no Homebrew ffmpeg needed) |
| Tests while developing | `make test T=parts`, `make test K=lamp`, `make test-pick`, `make test-changed`, `make test-failed`; `make test-list` shows the choices |
| Before hand-off | `make check` (ruff + contract drift + every test + web typecheck/build) |
| Self-score against the brief | `python3 scoring/score.py` |

## Detail levels and loading order

`make viewer` / `make viewer-auto` also split the scan into **5 additive detail levels** ([`scripts/lod.py`](scripts/lod.py)),
written as `lod/<k>.bin` (points) and `lod/<k>.splat` (splats). The split is a voxel pyramid per part. Level 0 keeps the
most important splat (opacity × size) in each 12 cm voxel of every part and of the unclaimed scan. Each next level
halves the voxel size (6, 3, 1.5 cm), and level 4 holds the rest. Together the levels are exactly the scan, with no row
twice. Level 0 is about 4 % of the rows, so a complete, coarse room is on screen after a small fraction of the download.

The viewer loads everything lazily, in this order, each step on screen as soon as it arrives (a thin bar along the top
shows progress, and the stats line shows `detail k/5`):

1. `scene.json`: the toolbar, the parts list, the part boxes.
2. Point levels 0 → 4, coarse to fine; points are drawn larger while finer levels are missing.
3. Splats, if switched on: the Spark module, then splat levels 0 → 4. The points stay on screen until the first splat
   level is sorted and drawn, so there is no blank frame. Phones and the Quest skip the finest splat level by default;
   `?splatlod=N` sets the budget.
4. The VR module, only where WebXR VR is supported, and only after the points are in.
5. Approval images, only when a card shows them.

The snapshot page still loads the full `scene.bin`, so snapshots draw every point. Exports made before the detail levels
existed still work: the viewer loads their single `scene.bin` / `scene.splat` instead.

## Gaussian splats

`make viewer` (and `make viewer-auto`) also writes `scene.splat` next to `scene.bin`: the same rows as SH-0 Gaussian
splats (position, scale, rotation, opacity, base colour), 32 bytes per splat in the `.splat` layout
([`scripts/splat_format.py`](scripts/splat_format.py)). Row *i* is the same splat in both files, so the viewer cuts
`scene.splat` into one Spark `SplatMesh` for the unclaimed scan and one per part, and gives each mesh the opacity and
tint of its role. Scan / Model / Overlay / Wireframe, Red / grey, the build replay, selection and the dollhouse cut
(a `SplatEdit` plane) all work on splats.

- Press **Splats** (or **G**, or open the viewer with `?render=splats`). The splat levels download on first use, coarse first, with progress
  on the button: about 52 MB for the 1.6 M-splat Equipment Room.
- **VR:** the right stick click switches too. Splats are much heavier than points on a headset, so start in Points and
  switch when you stand still. In VR, splats are cut at √5 standard deviations instead of 3 (about 40 % fewer pixels).
- Not on the snapshot page: `capture.html` stays point-based, so snapshots are reproducible.

## VR on Meta Quest 3

Browsers only offer WebXR on `https://` or `localhost`, so pick one of these:

- **Wi-Fi:** `make web-vr` serves HTTPS with a self-signed certificate on every interface. In Quest Browser open `https://<laptop-ip>:5173` (Vite prints the address), accept the certificate warning once, then press **Enter VR**.
- **USB cable:** `make web`, `adb reverse tcp:5173 tcp:5173`, then open `http://localhost:5173` in Quest Browser.

In VR you stand on the floor of the scanned room, on open floor away from the equipment, facing the selected part (or the pump). The reference space is `local-floor`, so your real eye height and every step you take carry over 1:1: walking a metre in your room walks a metre in the scan.

| Input | Action |
|---|---|
| Walk in your room | Walk in the scan (room-scale, 1 m = 1 m) |
| Left stick | Walk where you look (stops at the room walls) |
| Right stick left/right | 30° snap turn around your head |
| Right stick click | Points ↔ Gaussian splats |
| Trigger, or pinch with hand tracking | Teleport: aim the arc at the floor and release |
| Point at equipment or a pipe | Its box lights up and a label shows name, kind and point count |
| Squeeze (grip) while pointing | Select that part (red); squeeze again to clear |
| A / X | Cycle Scan → Model → Overlay |
| B / Y | Part boxes on/off |
| Left stick click | Back to the start point |

The left controller carries a small panel showing the current view. Metric scale is still unverified. VR assumes **1 u ≈ 1.15 m**, from the pallet jack's size and the 2.6 u ceiling height. Override it with `?mpu=<metres per unit>`. To hold 72 Hz, VR leaves out the finest [detail level](#detail-levels-and-loading-order), and when frames still run long it leaves out one more level at a time, down to level 2 of 5 (the wrist panel shows `LOD n/5`). The coarse levels are spatially even, so the room stays whole, only sparser. `?xrlod=N` pins VR to levels 0..N (`?xrlod=4` draws everything). Nothing is fetched at runtime (controllers are drawn as rays, hands as spheres), so the demo also runs offline.

## Repo map

| Path | What |
|---|---|
| [`docs/`](docs/README.md) | Readable versions of the partner files (challenge brief, Excel builder pack, PLY scans, videos) and a summary of every linked reference |
| [`Source-Data-Do-Not_change/`](Source-Data-Do-Not_change/) | Original partner files, read-only. `*.ply` / `*.mp4` are gitignored, see [docs/source-data](docs/source-data/README.md) |
| [`pipeline/`](pipeline/) | Offline Python. `build.py` + `stepbuild/` = the step-by-step build (cleaning filters, part detectors, CPU splat renderer, state and image numbering); `01_clean.py` = M1 clean loader; `05_bind_metadata.py` = xlsx dump + `AssetRecord` merge; `common/` = PLY reading, real-row detection, world orientation |
| [`build/`](build/) | Build state: `manifest.json`, `parts/*.idx.npy` and `removed/*.idx.npy` (splat indices into the master scan), earlier runs in `archive/`. The `.ply` files are rebuilt from the indices and stay local |
| [`images/`](images/) | One numbered image per build step: `NNNN_YYYYMMDD-HHMMSS.png`, numbering never restarts |
| [`web/`](web/) | three.js viewer of the step-by-step build (`index.html`: Scan / Model / Overlay / Wireframe, parts list, build replay; responsive for phones; click or tap a part in the room to select it; `src/xr.ts` = WebXR walk-through for Quest 3) and the URL-driven snapshot page `capture.html` (plan/elevation views with a grid, close-ups, captions). `make viewer` exports the build, `make web` serves it, `make snap` writes numbered PNGs to `images/` |
| [`api/`](api/) | FastAPI scaffold (`make api`, port 8000); also serves the step images to the viewer (`/api/images/{name}`) |
| [`contracts/`](contracts/) | Frozen shared types: pydantic (`py/`), TypeScript (`ts/`), exported JSON Schema (`json-schema/`). `make contracts` re-exports; `make check` fails on drift |
| [`scripts/`](scripts/) | `export_viewer_scene.py` (build → web), `timelapse.py`, `check_contracts.py`, `run_tests.py` (pick which tests to run) |
| [`tests/`](tests/) | pytest. Most tests use synthetic rooms; the few that read pipeline outputs (`01_clean.py`, `05_bind_metadata.py --dump`) skip until those files exist |
| [`pm_pack/`](pm_pack/) | PM pack for the locked wedge **Approve-to-Build Twin** (generated from the source data): partner briefing questions + phone card, PRD, SWOT, risk register, roadmap, `AGENTS` context ([`AGENTS.md`](AGENTS.md) links to `06`) |
| [`scoring/`](scoring/README.md) | The brief's judging rubric broken into 18 sub-criteria, plus a self-score script |
| [`research/`](research/) | Research notes: splat cleaning, semantic extraction, navigation, three.js/WebXR, offline AI copilot, curator + metadata binding. Start at [`00`](research/00_context_and_source_data.md) |
| [`solutions/`](solutions/README.md) | Eleven candidate solution designs (S1–S11) compared on requirements and speed |
| [`analysis/ply_study/`](analysis/ply_study/README.md) | Study of the boiler-room PLY (the random-bits tail, frame, dimensions), made with [`tools/ply_study.py`](tools/ply_study.py) |
| [`design/`](design/) | **Cyberpunk v2** theme: [`cyberpunk-tokens.css`](design/cyberpunk-tokens.css) and the [guide](design/CYBERPUNK_THEME.md) |

## Credits

The viewer's source modes (Scan / Model / Overlay / Wireframe) and the snapshot page (`web/capture.html`: orthographic plan/elevation views, section cut, 0.25 u grid, readiness flag for scripted screenshots) are adapted from [wesbos/3d-model-anything](https://github.com/wesbos/3d-model-anything) (MIT, © 2026 Wes Bos). Only code ideas were reused; none of its `data/` assets are included.

## autoscene: automatic object detection and room rebuild

[`autoscene/`](autoscene/README.md) turns the splat scan into a room of named, framed objects with no human in
the loop: a numba Gaussian-splat rasteriser renders 197 views with an ID buffer, YOLOE-26 finds objects in them,
the masks are lifted to 3D by view-consensus merging, the ceiling pipe network is split into runs by local
direction, and every object gets its own PLY, an oriented box, a row in `out/scene.json` and three pictures
(textured close-up, room-so-far from outside, detector proof). Plan and research: [`autoscene/PLAN.md`](autoscene/PLAN.md).

```bash
cd autoscene && uv sync && uv run python -m autoscene.run all
```

To see the automatic build in the web viewer (build slider, boxes, cutaway, VR), export it and open the viewer with
`?scene=auto`:

```bash
make viewer-auto && make web     # then http://localhost:5173/?scene=auto
```
