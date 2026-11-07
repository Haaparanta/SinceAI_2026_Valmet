`// VALMET × SINCE AI 2026 · PM PACK · 03`

# 03 — Strategic SWOT & Competitor Matrix

Where Approve-to-Build wins on the judging sheet, where it is honestly thin, and what the three predictable "lazy" readings of the same source data look like next to it.

`v1.0.0 · GENERATED 2026-11-06 20:45 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data; the question lives in `01_Partner_Briefing_Questions.md`. `[HYPOTHESIS]` = our deduction or design choice. Team roles are slots (**PM / CV / AI / FE**) because the team composition was not given; map them to names on Friday night.

---

## 1. SWOT — 2 × 2

| | **HELPFUL** | **HARMFUL** |
|---|---|---|
| **INTERNAL** | **Strengths** <br>• **Human approval turns an unreliable segmentation into a verified count.** Clustering on a 3DGS scan that is 67 % garbage `[SOURCE DATA — measured]` will over- and under-segment; the one-by-one curator (`M4`) means every object the judges see was checked, and the on-screen metric says so (`100 % human-verified`). `[HYPOTHESIS]` <br>• **We implement the pack's own contract.** `DOC-3D-MAPPING`: "Map visible objects to stable asset IDs with explicit confidence … Never silently guess identity." `[SOURCE DATA]` Approval sets `mapping_confidence: 1.0`; unbound objects are explicit `context` objects, never guessed. <br>• **`Scene_Anchors` is designed to be replaced.** Every row says `placeholder_until_valmet_scene_received` and `remap_instruction: "Remap to real scene path and bounds when Valmet splat arrives."` `[SOURCE DATA]` We are the team that actually remaps it (`M6`). <br>• **One grid, two consumers.** The same dilated occupancy grid (`M2`) drives the avatar route (`M7`) and the first-person walk (`M10`), so a judge who grabs the keyboard cannot clip through a boiler either. `[HYPOTHESIS]` <br>• **Offline pipeline + Demo Mode.** All geometry is pre-computed (`M1`–`M3`, `M7`); `DEMO_MODE=1` (`M11`) replays cached diagnoses with Wi-Fi off. <br>• **The snapshot timelapse (`M5`) is free marketing**: 100+ PNGs become the first 30 s of the video and a slide. | **Weaknesses** <br>• **Team composition unknown** — hours in `02` assume 3–4 people; with 2 the SHOULD list is gone. `[HYPOTHESIS]` <br>• **~53 MUST hours** against ~37 wall-clock hours; the critical path runs CV → FE. <br>• **Human-in-the-loop may read as "less automated"** under criterion 4 ("well-structured, automated, and modular" `[SOURCE DATA — brief §06]`) and criterion 1 ("process … to extract" `[SOURCE DATA — brief §02]`). `[GAP - ASK PARTNER]` G4. <br>• **Density ceiling.** Geometric clustering on ~400 k clean points yields tens, not hundreds, of clean objects; the demo videos' "every object, its own asset" look needs `S1` labels and `S5` merge/split to approach. `[HYPOTHESIS]` <br>• **VR is a stretch** (`S3`): HTTPS, headset performance, controller locomotion — all untested on this scene. <br>• **No GPU confirmed**, Homebrew Python 3.15 without wheels — the first hour is environment work. `[SOURCE DATA — local tooling]` |
| **EXTERNAL** | **Opportunities** <br>• **The pack's `API_Contract` sheet is a spec we can fulfil literally** (`/api/assets`, `/api/assets/{id}`, `/api/scene/anchors`, `/api/copilot/query`, `/api/work-orders/draft`). `[SOURCE DATA]` Judges from the same organisation that wrote it will recognise their own routes. <br>• **`Builder_Questions` P0s map one-to-one onto our MUSTs**: Q-01 identify in 3D + state + evidence + docs (`M4`/`M6`/`M9`), Q-03 explain with exact evidence IDs and confidence (`M9`), Q-05 3D object → evidence → service case (`M9`/`C1`), Q-06 reduce confidence when mapping quality is poor (`M6` mapping confidence). `[SOURCE DATA]` <br>• **The dirty PLY is a story, not just a problem**: "1.5 M gaussians, a third usable, and here is the cleaned room" is a credible opening for criterion 4. `[SOURCE DATA — measured]` <br>• **Mentoring windows** let us show an ugly end-to-end prototype at the first one and correct course while other teams are still rendering. `[SOURCE DATA — brief §08]` <br>• **Quest 3 walk** is an innovation moment no lazy reading can match (criterion 5). | **Threats** <br>• **Judges may expect fully automatic extraction** and score the approved count as "manual labelling". `[GAP - ASK PARTNER]` G4 — mitigated by reporting the automatic-only count beside the approved count (`04`, R5). <br>• **Scale or up-axis differ from our measurement** (y-up, ≈ 8.6 × 4.4 × 2.6 u `[SOURCE DATA — measured]`; metric scale unverified `[GAP - ASK PARTNER]` G1) → clearance and eye-height constants are wrong. <br>• **Referenced data is missing**: `telemetry_full_14d_30min.csv` and the 38 `DOC-*.md` files exist only as references `[SOURCE DATA — START_HERE, RAG_Corpus_Index]`; a team that gets them from the partner first has a richer RAG. <br>• **A CV-heavy team with a GPU** runs SAM/CLIP lifted to 3D `[SOURCE DATA — brief §04]` and posts a higher raw count. <br>• **NDA / public-repo / cloud-LLM limits** unknown `[GAP - ASK PARTNER]` G6. <br>• **Venue Wi-Fi, laptop GPU, headset battery** at demo time. |

### Why the source data is our advantage `[HYPOTHESIS]`

The brief is unusually prescriptive — four numbered capabilities, five weighted criteria, a named faulty-device workflow — and the xlsx is not a dataset but a **product spec in disguise**: an API contract, ten builder questions with priorities, an evidence-citation contract (`DOC-RAG-GUIDE`), a safety guardrail (`DOC-FIELD-SAFETY`) and a mapping layer that announces it wants to be replaced. `[SOURCE DATA]` Most teams will read the brief's buzzwords (splats, SAM, NavMesh, RAG) and build one of them well. Approve-to-Build reads the *spreadsheet* and builds the thing the spreadsheet was written for: a scene graph where every object has a stable ID, an explicit confidence, evidence behind its status and a safe next step — then walks the judges through it, on a laptop and in a headset.

---

## 2. Competitor matrix — our wedge vs three lazy interpretations

Columns 2–4 are predictions of what other teams will build from the same package `[HYPOTHESIS]`.

| DIMENSION (WEIGHT) | **US · Approve-to-Build Twin** | **LAZY 1 · "Maintenance chatbot"** <br>RAG over the xlsx, no 3D | **LAZY 2 · "Pretty splat viewer"** <br>photoreal splat, hand-placed hotspots, scripted camera | **LAZY 3 · "Segmentation notebook"** <br>automatic clustering, no navigation, no metadata |
|---|---|---|---|---|
| c1 Extraction density & 3D framing (30 %) | ✅ tens of verified OBBs + `S1` labels; honest count on screen | ❌ no scene processing at all | ❌ a handful of manual hotspots, no framing | ⚠️ highest raw count, but unverified and over-segmented |
| c2 Collision-free navigation & proximity (25 %) | ✅ A* on a measured occupancy grid, same grid for first-person walk, proximity ring | ❌ nothing moves | ⚠️ a camera path keyed by hand — looks right, proves nothing | ❌ absent |
| c3 AI diagnostics, grounding, explainability (20 %) | ✅ `Diagnosis` JSON with validated evidence IDs, confidence, next safe check (`DOC-RAG-GUIDE`) | ✅ this is the whole product; often strong | ❌ a text popup at best | ❌ absent |
| c4 Backend architecture (15 %) | ✅ 7-step offline pipeline + FastAPI implementing `API_Contract`; ⚠️ approval step is human | ⚠️ one script around an LLM | ⚠️ renderer config, little backend | ✅ a clean pipeline, but it stops at clusters |
| c5 Demo clarity & innovation (10 %) | ✅ snapshot timelapse, walk, Quest 3 | ⚠️ chat windows all look alike | ✅ gorgeous first 10 s, then nothing happens | ❌ a notebook on a projector |
| Reliability of the live demo | ✅ Demo Mode, pre-computed artifacts, Wi-Fi-off rehearsal | ⚠️ depends on a live LLM | ✅ a video of itself | ⚠️ depends on the kernel not dying |
| Evidence of understanding the brief | ✅ all four numbered capabilities visible on one screen | ❌ ignores items 1, 3, 4 | ❌ ignores items 1 and 3 | ❌ ignores items 2, 3, 4 |
| Monday usefulness to Valmet | ✅ a curated scene graph + API a real twin could ingest | ⚠️ a chatbot they already have vendors for | ❌ a screensaver | ⚠️ raw clusters need the step we did |
| **Expected score (0–100)** `[HYPOTHESIS]` | **≈ 82** | ≈ 38 | ≈ 34 | ≈ 41 |

> [!TIP]
> The weights punish every lazy reading in the same way: each one maxes out **one** criterion and forfeits at least 45 % of the sheet. Our risk is the opposite — being good at everything and spectacular at nothing — which is why the snapshot timelapse and the Quest walk exist.

---

## 3. What we say at the stand when asked about the lazy options

- **"Why not a chatbot over the Excel?"** — "We have that; it is the last 20 seconds of our demo. The other 80 % of the brief is about *where* the pump is and *how* to reach it, so the copilot only speaks once the avatar has arrived — and every ID it cites is a row you can open."
- **"Why not just render the splat beautifully?"** — "We do render it `[S4]`, but a splat is 1.5 million gaussians that don't know they are a boiler. We approved each object into a scene graph with a stable asset ID, which is what your `Scene_Anchors` sheet asked for `[SOURCE DATA]`."
- **"Why isn't the extraction fully automatic?"** — "It is automatic up to the proposal; a human approves because your `DOC-3D-MAPPING` doc says never to guess identity silently `[SOURCE DATA]`. We show both numbers: what the pipeline found on its own and what a person verified. Monday morning, that approval step is the five minutes a service expert spends before trusting a twin."
