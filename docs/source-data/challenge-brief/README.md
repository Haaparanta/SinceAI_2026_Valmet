# Challenge brief

Source: [`Valmet_x_SinceAI_2026_Challenge_Brief_FINAL_updated (1).docx`](../../../Source-Data-Do-Not_change/) · Since AI Hackathon 2026 · 6–8 Nov 2026, Turku · partner: **Valmet Automation**

## Title

**Industrial Metaverse: Semantic 3D Scene Understanding & Autonomous Field-Service Copilot**

## Guiding question

> How might we extract maximum semantic asset information and walkable paths from Industrial Boiler Room.ply so a simulated service avatar or robot can realistically navigate to a faulty device, dynamically display 3D-framed nearby assets mapped from synthetic metadata, and deliver AI service guidance?

## Problem

Field-service staff and inspection robots have to move through complex plants, recognise equipment, know its condition and decide what to check next. That context is split across the physical space, automation and condition data, and maintenance documents.

3D Gaussian Splatting and LiDAR can capture a plant photorealistically and fast, but the capture is semantically "blind": it does not know where the floor is, where the walls and obstacles are, or which points belong to which machine. Valmet wants to see that meaning extracted from the boiler-room splat to drive a field-service simulation.

Valmet explicitly says: **do not spend time on a mobile/Android frontend.** Put the effort into backend intelligence, dense semantic extraction and realistic spatial simulation.

## What to build (the four steps)

1. **Extract and 3D-frame assets from `Industrial Boiler Room.ply`.** Detect, segment and put 3D bounding boxes around equipment and surrounding objects, in the style of the two demo videos. *More assets is better*: it gives the navigating agent richer awareness.
2. **Map the synthetic metadata from the Excel builder pack** onto the extracted assets: statuses, metadata, telemetry. The mapping does **not** need to be physically correct. Random or procedural assignment is explicitly allowed.
3. **Simulate collision-free avatar or robot navigation** to a pre-chosen faulty device. The route can be computed automatically but must be a believable walkable path that avoids walls, boilers, piping and other obstacles.
4. **Show nearby assets and run AI diagnostics.** While walking, every extracted asset near the avatar is highlighted with its 3D frame and mapped metadata. On arrival at the faulty device, an AI assistant diagnoses the condition and recommends next inspection/service steps, grounded in the Excel pack.

**Technical freedom:** any language (Python and Rust are named). Any viewer once the scene is processed: Rerun, Open3D, Viser, PyVista, a web viewer (Three.js), Unity, Unreal or Omniverse/OpenUSD. Easy UI is strongly preferred.

## Suggested AI approaches (optional)

| Area | Suggested techniques |
|---|---|
| Dense semantic extraction and 3D framing | point-cloud/splat segmentation, clustering, SAM/CLIP on multiple views lifted to 3D, geometric heuristics |
| Obstacle-aware pathfinding | floor/walkable surface extraction, 2D/3D occupancy grids, voxel traversal, NavMesh, A*, RRT* |
| Proximity awareness | query frames, labels and status of every asset within a radius of the avatar as it moves |
| Metadata mapping | bind IDs, statuses, telemetry and attributes from the Excel pack (random or rule-based is fine) |
| RAG / AI copilot | LLM or agent grounded in the pack's telemetry, alarms and troubleshooting notes; explain the fault and suggest safe inspection steps |
| Lightweight visualisation | Rerun, Open3D, Viser, PyVista, Three.js, Unity, Unreal, Omniverse/OpenUSD |

## Data provided

1. **`Industrial Boiler Room.ply`**: the base 3DGS environment for extraction, framing and navigation. → [boiler-room-ply/](../boiler-room-ply/README.md)
2. **`semantic extraction demo 1.mp4` and `demo 2.mp4`**: reference videos of the desired output ("Every object, its own asset"; indoor industrial mesh with bounding-frame tagging). Inspiration only. → [demo-videos/](../demo-videos/README.md)
3. **`Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack.xlsx`**: equipment master data, status and condition signals (temperature, vibration, pressure/flow proxy, health), alarms, event logs, maintenance history, service instructions and troubleshooting notes for RAG. → [builder-pack/](../builder-pack/README.md)

**Mapping rule:** you *must* use the Excel values to populate statuses and metadata. Physical accuracy is not required: give normal statuses to assets along the path and a faulty/warning status to the target device.

## Scoring

| # | Criterion | Weight | What judges look for |
|---|---|---:|---|
| 1 | Semantic asset extraction density & 3D framing | **30%** | How many objects are extracted, framed and mapped to Excel metadata |
| 2 | Obstacle-aware navigation & proximity display | **25%** | A logical floor path to the faulty device that never clips through solids; nearby assets shown dynamically |
| 3 | AI diagnostics, grounding & explainability | **20%** | Correct status explanations along the path and grounded troubleshooting at the target |
| 4 | Backend architecture & implementation | **15%** | Well-structured, automated, modular pipeline |
| 5 | Demo clarity & innovation | **10%** | Easy to follow, runs reliably |

Valmet's own summary: a lightweight viewer that frames *many* assets, computes a realistic collision-free path, maps the Excel data and delivers smart AI diagnostics beats a polished mobile app with weak spatial processing.

## Submission

The demo must, at minimum:

- process the PLY and 3D-frame as many assets as possible
- map Excel statuses, telemetry and metadata to those assets (procedural is fine), including one **pre-determined faulty target**
- walk an avatar or robot along an automatic, logical, collision-free path to it
- highlight frames and Excel metadata for nearby assets along the way
- trigger an AI diagnostic and service-guidance workflow at the target
- run on any easy UI (Python viewer, web app, game engine)

Deliverables:

- [ ] working demo, runnable locally or clearly recorded
- [ ] source repo with a concise README and setup instructions
- [ ] 5–8 slides: extraction pipeline, pathfinding logic, Excel mapping, AI approach
- [ ] demo video, **max 5 minutes**: navigation in the boiler room, framing nearby assets, diagnosing the faulty device
- [ ] short technical note listing models, libraries and software components

## Every requirement, traced

Each "must" in the brief, where it is stated, which score it feeds, and what in our build covers it.

| # | Requirement | Brief section | Score | Our component | Done when |
|---|---|---|---|---|---|
| R1 | Process `Industrial Boiler Room.ply` | 02, 07 | 1 | loader + cleaner ([PLY doc](../boiler-room-ply/README.md)) | cleaned cloud cached; junk ratio reported |
| R2 | Detect and segment as many objects as possible | 02 step 1, 04, 06.1 | 1 (30%) | clustering + labelling | object count on screen, aim ≥ 50 |
| R3 | 3D bounding box / frame around each | 02 step 1, 07 | 1 | box fitting (oriented if time allows) | every object has a frame in the viewer |
| R4 | Map Excel statuses, telemetry, metadata to extracted assets | 02 step 2, 05, 07 | 1, 3 | mapping layer replacing `Scene_Anchors` | each mapped box shows tag + health |
| R5 | Designate one pre-determined faulty target | 05, 07 | 2, 3 | config value (P-005 recommended) | target highlighted at start |
| R6 | Normal statuses on assets along the path, faulty status on the target | 05 | 1, 3 | mapping rules | path passes green/amber assets before the red one |
| R7 | Avatar or 3D robot | 02 step 3, 07 | 2 | viewer primitive | visible moving body |
| R8 | Automatically defined path | 02 step 3, 07 | 2 | floor extraction + occupancy grid + A* | path computed, not hand-drawn |
| R9 | Path follows a logical, walkable route; never through walls, boilers, piping or obstacles | 02 step 3, 06.2 | 2 (25%) | inflated occupancy grid | path rendered on the floor, no clipping in the video |
| R10 | Nearby assets highlighted dynamically with frame + metadata | 02 step 4, 04, 06.2, 07 | 2 | proximity query per frame | panel/labels update as the avatar moves |
| R11 | AI diagnosis on arrival at the faulty device | 02 step 4, 07 | 3 (20%) | copilot query | answer appears automatically at the target |
| R12 | Recommend next inspection/service steps grounded in the Excel data | 02 step 4, 04, 06.3 | 3 | RAG over Knowledge_Docs, cases, events, telemetry | answer cites IDs and confidence |
| R13 | AI explains status of devices along the path (not only the target) | 06.3 | 3 | short copilot blurbs or rule-based summaries | each nearby asset has a one-line explanation |
| R14 | Modular, automated backend | 06.4 | 4 (15%) | pipeline split into stages with cached outputs | one command rebuilds everything |
| R15 | Any easy UI; runs reliably | 02, 06.5, 07 | 5 (10%) | Python or web viewer | demo runs start to finish without manual steps |
| R16 | Repo with concise README and setup instructions | 07 | 4, 5 | root README | fresh clone to running demo in < 5 min |
| R17 | 5–8 slides | 07 | 5 | deck | covers extraction, pathfinding, mapping, AI |
| R18 | Demo video ≤ 5 min | 07 | 5 | screen recording | uploaded |
| R19 | Technical note: models, libraries, components | 07 | 4 | `TECHNICAL_NOTE.md` | lists every model and library with version |

## What is explicitly allowed or not required

- **Random or procedural mapping** of Excel rows to 3D objects. Physical accuracy is not expected. (05, 02 step 2)
- **Any language, any viewer.** Python and Rust are named; Rerun, Open3D, Viser, PyVista, Three.js, Unity, Unreal and Omniverse are all fine. (02, 04)
- **Recorded demo** instead of a live one. (07: "runnable locally … or clearly recorded")
- **No mobile app needed**; Valmet actively discourages it. (02, 06)
- An **automatically defined** path is fine; it does not need to be interactive. (02 step 3)

## Ambiguities worth asking a Valmet mentor about

1. **Scale.** The cleaned scan is about 2 units floor-to-ceiling, which looks too low for metres. Do they know the real dimensions?
2. **Counting objects.** Does a pipe segment or a box of clutter count as an "asset" for criterion 1, or only equipment?
3. **Missing files.** The pack refers to a 14-day telemetry CSV and 38 Markdown docs that were not delivered. Can we get them?
4. **Robot vs person.** Is either equally good, or do they prefer one (e.g. a wheeled inspection robot with a larger clearance)?
5. **LLM choice.** Any restriction on cloud LLMs, or a preference for local models?

## Event timeline

| When (EET) | What |
|---|---|
| Fri 6 Nov 2026, 19:30 | Build starts |
| During the event | Valmet mentoring windows (the brief says "agreed windows" but gives no times; check Discord) |
| Sun 8 Nov, 10:00 | Submission deadline |

## Contacts

| Who | Role | Contact |
|---|---|---|
| Mika Karaila | Valmet | mika.karaila@valmet.com |
| Alp Aydin | Valmet partners | alp.aydin@valmetpartners.com |
| Riku Lauttia | Since AI (template questions) | riku.lauttia@sinceai.fi |

General builder questions go to the **Since AI Discord challenge channel**. Valmet staff answer domain questions during the agreed mentoring windows.
