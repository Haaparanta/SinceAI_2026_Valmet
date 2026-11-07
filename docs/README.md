# docs/

Readable Markdown versions of everything Valmet and Since AI handed us, plus one summary per external link in the data pack. Use these instead of opening the `.docx` / `.xlsx` every time.

The originals in [`Source-Data-Do-Not_change/`](../Source-Data-Do-Not_change/) stay the source of truth. If a doc here disagrees with them, the original wins.

## Source data

| Doc | Covers |
|---|---|
| [source-data/](source-data/README.md) | Inventory of every partner file, sizes, checksum, what is in git and what is not |
| [source-data/challenge-brief/](source-data/challenge-brief/README.md) | The official challenge brief: problem, four build steps, scoring weights, submission package, contacts |
| [source-data/builder-pack/](source-data/builder-pack/README.md) | The synthetic Excel pack, all 16 sheets: columns, distributions, how sheets join, telemetry fault signatures, faulty-target choice and a P-005 dossier |
| [source-data/builder-pack/data-reference/](source-data/builder-pack/data-reference/README.md) | Every row of the small sheets: 30 assets, states, anchors, per-asset evidence counts, 50 service cases, 38 RAG docs |
| [source-data/boiler-room-ply/](source-data/boiler-room-ply/README.md) | The original 3D Gaussian Splatting scan (the build now uses `Equipment Room.ply`, see [source-data/](source-data/README.md#equipment-roomply)): attribute decoding, junk statistics, room dimensions, floor/ceiling heights, cleaning code |
| [source-data/demo-videos/](source-data/demo-videos/README.md) | The room walkthrough and the two "semantic extraction" reference videos, with contact sheets and an inventory of what is in the room |

## Linked references

The builder pack's `Public_Research` sheet cites nine public pages. Each has its own summary:

| # | Doc | Source |
|---|---|---|
| 1 | [Valve digital services](links/01-valmet-valve-digital-services/README.md) | Valmet |
| 2 | [AI-assisted valve diagnostics 2026](links/02-valmet-valve-diagnostics-blog-2026/README.md) | Valmet blog |
| 3 | [Valmet Virtual Mill](links/03-valmet-virtual-mill/README.md) | Valmet |
| 4 | [Virtual Maintenance Hub](links/04-valmet-virtual-maintenance-hub/README.md) | Valmet |
| 5 | [Condition Monitoring](links/05-valmet-condition-monitoring/README.md) | Valmet |
| 6 | [OPC UA for Asset Administration Shell](links/06-opc-ua-asset-administration-shell/README.md) | OPC Foundation |
| 7 | [OPC Cloud Initiative, June 2026](links/07-opc-cloud-corner-june-2026/README.md) | OPC Foundation |
| 8 | [glTF Gaussian Splatting extension](links/08-khronos-gltf-gaussian-splatting/README.md) | Khronos |
| 9 | [OpenUSD Gaussian Splats (Particle Fields)](links/09-nvidia-openusd-particle-fields/README.md) | NVIDIA |

See [links/](links/README.md) for the one-page overview of what each link means for our build.

## Our results

| Doc | Covers |
|---|---|
| [build_comparison.md](build_comparison.md) | Manual (human-approved) vs automatic build, part by part: which manual parts the automatic build matched, split into pieces, partly found or missed, and what it found that the manual build lacks. Regenerate with `make compare` |

## Start here

New to the challenge? Read in this order:

1. [Challenge brief](source-data/challenge-brief/README.md): what to build and how it is scored, with a requirement-by-requirement trace.
2. [Videos](source-data/demo-videos/README.md): what the room looks like and what "good" extraction looks like.
3. [PLY scan](source-data/boiler-room-ply/README.md): how to read it and why most of it must be thrown away. The build now runs on the newer, clean [`Equipment Room.ply`](source-data/README.md#equipment-roomply).
4. [Builder pack](source-data/builder-pack/README.md): the data to map, the fault signatures, and the recommended faulty target (P-005).
5. [Links overview](links/README.md): Valmet's own products and the standards behind the pitch.

## How these were made

- `.docx` and `.xlsx` were parsed directly from their XML on 2026-11-06. Every number in the builder-pack docs was counted from the file, not copied from its Dashboard sheet. The [full data reference](source-data/builder-pack/data-reference/README.md) is generated from the Excel.
- PLY statistics come from a full-file NumPy pass over all 1,506,136 Gaussians.
- Video facts come from ffmpeg metadata and sampled frames; the contact sheets are in [source-data/demo-videos/img/](source-data/demo-videos/img/).
- The nine web pages were read on 2026-11-06, plus two companion sources (the glTF spec README and the OpenUSD converter script). Summaries are in our own words. Links 1–3 and 6–9 were read from the page text itself; for links 4 and 5 the Valmet site buried the body under menu markup, so those rest on an extracted reading. Check the live page before quoting a specific claim from 4 or 5 in the pitch.
