`// SINCE AI 2026 × VALMET`

# SinceAI_2026_Valmet

Making scanned industrial plants understand themselves: where equipment is, what it is, how to reach it, and why it needs attention.

`HACKATHON · BUILD FRI 19:30 EET · DEADLINE SUN 10:00 · STATUS: BUILD · WEDGE: APPROVE-TO-BUILD TWIN`

## Hackathon Challenge

Imagine entering a digital industrial plant where the environment does more than look real. It understands where machines are, what they are, how people or robots could move between them and which equipment needs attention. Today's 3D captures can be visually extraordinary—but they often lack the meaning needed for intelligent action.

Valmet challenges you to bridge that gap. Explore how spatial perception, semantic 3D understanding and AI-grounded equipment information could transform a scanned industrial environment into a navigable, useful digital world. Think computer vision, point-cloud intelligence, digital twins, robotics simulation and an assistant that can explain the context behind a maintenance decision.

This is a chance to make AI understand not just words and numbers, but physical space. A strong demonstration could point toward industrial operations where service experts and autonomous systems find the right equipment faster, navigate complex facilities more intelligently and turn fragmented technical data into confident, context-aware action.

## Repo map

| Path | What |
|---|---|
| [`docs/`](docs/README.md) | Readable versions of the partner files (challenge brief, Excel builder pack, PLY scan, videos) and a summary of every linked reference |
| [`Source-Data-Do-Not_change/`](Source-Data-Do-Not_change/) | Original partner files, read-only. `*.ply` / `*.mp4` are gitignored, see [docs/source-data](docs/source-data/README.md) |
| [`pm_pack/`](pm_pack/) | PM pack for the locked wedge **Approve-to-Build Twin** (generated from the source data): partner briefing questions + phone card, PRD, SWOT, risk register, roadmap, `AGENTS` context |
| [`research/`](research/) | Research notes: splat cleaning, semantic extraction, navigation, three.js/WebXR, offline AI copilot, curator + metadata binding. Start at [`00`](research/00_context_and_source_data.md) |
| [`design/`](design/) | **Cyberpunk v2** theme: [`cyberpunk-tokens.css`](design/cyberpunk-tokens.css) and the [guide](design/CYBERPUNK_THEME.md) |
| [`web/`](web/) | three.js viewer of the step-by-step build (`index.html`: Scan / Model / Overlay / Wireframe, parts list, build replay) and the URL-driven snapshot page `capture.html` (plan/elevation views with a grid, close-ups, captions). `make viewer` exports the build, `make web` serves it, `cd web && npm run snap -- "<query>"` writes numbered PNGs to `images/` |

## Credits

The viewer's source modes (Scan / Model / Overlay / Wireframe) and the snapshot page (`web/capture.html`: orthographic plan/elevation views, section cut, 0.25 u grid, readiness flag for scripted screenshots) are adapted from [wesbos/3d-model-anything](https://github.com/wesbos/3d-model-anything) (MIT, © 2026 Wes Bos). Only code ideas were reused; none of its `data/` assets are included.
