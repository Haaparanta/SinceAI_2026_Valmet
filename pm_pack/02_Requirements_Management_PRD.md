`// VALMET × SINCE AI 2026 · PM PACK · 02`

# 02 — Requirements & PRD: Approve-to-Build Twin

A human-approved semantic twin of the Industrial Boiler Room. Objects are proposed by an offline pipeline, approved **one by one** in a web curator, **photographed on every approval** (new object red, the rest see-through grey), then **walked in three.js** — on a laptop for the judges and on a Meta Quest 3 for the wow moment.

`v1.0.0 · GENERATED 2026-11-06 20:40 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data; the question lives in `01_Partner_Briefing_Questions.md`. `[HYPOTHESIS]` = our deduction or design choice. Team roles are slots (**PM / CV / AI / FE**) because the team composition was not given; map them to names on Friday night.

---

## 0. The locked wedge in one breath

| | |
|---|---|
| **Name** | **Approve-to-Build Twin** (code name `a2b`) |
| **Tagline** | *Every object, approved. Every approval, photographed. Then walk it.* |
| **One sentence** | An offline Python pipeline turns the 1.5 M-gaussian scan into a queue of object proposals; a web curator shows them one at a time and a human approves each into the central scene graph, which snapshots itself after every addition; the finished twin is a three.js web app in which a service avatar auto-walks a collision-free route to the faulty pump and a grounded copilot explains why — and the same scene opens in WebXR on a Quest 3. |
| **Your five non-negotiables** `[SOURCE DATA — your message]` | (1) objects identified **one by one**, added to the central scene only on **user approval**; (2) a **web interface** for that approval; (3) the **model work runs offline**, not live in the browser; (4) **after every addition a photo**: new object **red**, everything else **see-through grey**; (5) final demo **in the web, three.js, walkable**, with **Meta Quest 3** compatibility as a stretch goal. |
| **Interpretation of (3)** `[HYPOTHESIS]` | "Model offline" = the heavy work (cleaning, segmentation, proposal generation, meshing, routing) is a batch pipeline that writes JSON/binary artifacts; the browser only reviews and renders. We also make the whole demo **work with Wi-Fi off** (cached copilot answers, optional local LLM), which covers the other reading of "offline". |
| **Why it wins the Valmet track** `[HYPOTHESIS]` | Human-verified extraction gives a **high, honest asset count** (criterion 1, 30%), the same occupancy grid drives both the avatar and the first-person walk so nobody clips through a boiler (criterion 2, 25%), the copilot follows the pack's own `DOC-RAG-GUIDE` contract (criterion 3, 20%), the pipeline is modular by construction (criterion 4, 15%), and the snapshot timelapse + VR walk make the demo unforgettable (criterion 5, 10%). The pack itself asks for exactly this mapping discipline: `DOC-3D-MAPPING` — "Map visible objects to stable asset IDs with explicit confidence … Never silently guess identity." `[SOURCE DATA]` |

---

## 1. Monday-morning persona & quantified before/after

**Primary user** `[SOURCE DATA]`: "industrial field-service personnel and autonomous inspection robots" who must "navigate complex physical plants, identify surrounding equipment, understand current device conditions, and decide what to inspect or service next" (brief §02).

**Persona** `[HYPOTHESIS]`: **Jonna, Valmet field-service expert**, sent to a customer mill she last visited two years ago. The condition system flags `P-005` (`ASSET-017`, process pump, Utility Island, A-production-critical) with `FOULING`, health score 44, urgency high `[SOURCE DATA — Current_State]`. Secondary persona: **an inspection robot** that needs the same route and the same asset context as machine-readable JSON.

### Before — today `[HYPOTHESIS]` (baseline numbers are `[GAP - ASK PARTNER]`, question Q7)

| Step | What happens | Est. time |
|---|---|---|
| 1 | Reads the alarm, looks up the asset in the maintenance system | ~5 min |
| 2 | Hunts for the trend, recent events and the right guidance doc across three systems ("fragmented across physical spaces, automation/condition data, and maintenance documentation" — brief §02) | ~20–40 min |
| 3 | Asks the local operator where `P-005` physically is | ~5–15 min |
| 4 | Walks the plant, takes a wrong turn around blocked piping | ~10–20 min |
| 5 | Decides what to check with partial context | — |
| | **Time to first informed action** | **~40–80 min** |

### After — with Approve-to-Build `[HYPOTHESIS]`

| Step | What happens | Est. time |
|---|---|---|
| 1 | Opens the twin; `P-005` already glows `ALERT` | ~10 s |
| 2 | Taps **Walk to P-005**: a collision-free route draws on the floor | ~2 s |
| 3 | Follows the avatar (or walks first-person); every asset she passes shows its status chip and two metadata fields | ~2–4 min |
| 4 | At the pump, the copilot card shows: observation, hypothesis, confidence, the exact telemetry/event/doc IDs it used, and the **next safe check** | ~20 s |
| 5 | One tap drafts the work order (COULD) | ~10 s |
| | **Time to first informed action** | **~5 min** |

**Headline claim for the pitch** `[HYPOTHESIS]`: "From alarm to an evidence-backed first action in about five minutes instead of an hour — and the robot gets the same route as JSON."

---

## 2. The One-Screen Product

The product has **two screens that share one scene graph**. The judges see Screen B; Screen A is how Screen B got its assets, and its snapshot timelapse is the first 30 seconds of the video.

### Screen A — Curator (`/curate`, built Saturday, shown in the video)

| Element | Spec |
|---|---|
| **Scene** | The cleaned scan as a grey point cloud (`scene_points.bin`, ≤ 400 k points). Already-approved objects render as translucent grey meshes/boxes. |
| **The proposal** | Proposal `k` of `N` is drawn **red** (its points + its oriented bounding box), camera auto-frames it. Side panel shows: auto label guess, auto confidence, size in units, suggested `asset_id` (next free xlsx asset of the matching class) with a dropdown to change it or choose "context object (no xlsx row)". |
| **Actions** | **Approve** (`A`), **Reject** (`R`), **Skip** (`S`), **Relabel** (`L`, focuses the label input). Keyboard-first so 100+ decisions take under 40 minutes. |
| **On Approve** | `POST /api/proposals/{id}/approve` → object appended to `scene_graph.json` with `approved_by`, `approved_at`, `mapping_confidence: 1.0` → the browser re-renders the central scene **(new object red, all other approved objects grey at 25 % opacity, raw points hidden)** from a fixed isometric camera → `canvas.toDataURL()` → `POST /api/snapshots` → `data/snapshots/0042_obj-0042_P-005.png`. |
| **Progress** | `42 / 137 proposals · 31 approved · 9 rejected · 2 skipped`, with a thumbnail strip of the last five snapshots. |

### Screen B — Twin (`/`, the judges' screen)

| Element | Spec |
|---|---|
| **1 Input** | **Target device** selector with three pre-loaded sample buttons `[SOURCE DATA — Current_State attention_required]`: **`P-005 · FOULING`** (default, `ASSET-017`), **`M-006 · OVERHEATING`** (`ASSET-024`), **`P-002 · CAVITATION_RISK`** (`ASSET-014`). Each button sets the fault, plans the route and starts the walk. |
| **1 Central view** | three.js scene: the room (points, or the splat itself when S4 lands), approved objects as wireframe boxes/meshes coloured by status with a text label (`P-005 · PUMP · ALERT` — status is never colour-only), the route as a glowing polyline on the floor, the avatar/robot walking it, a **proximity ring** (radius 1.5 u `[HYPOTHESIS]`) that highlights assets as they come into range and shows two metadata fields (`condition_state`, `health_score`). Modes: **Follow avatar** (default), **Walk** (first-person, WASD + mouse, collision on the same grid), **VR** (WebXR button, Quest 3). |
| **1 Actionable output** | **Diagnosis card** on arrival: observation(s), hypothesis, confidence, `evidence_ids[]` (telemetry window, event IDs, doc IDs — every ID is a link that opens the row), **next safe check**, safety note from `DOC-FIELD-SAFETY`, and a **Draft work order** button (COULD). |
| **2 Proof metrics** (always visible in the status bar) | **`ASSETS · 87 approved · 30 bound to xlsx · 100 % human-verified`** and **`ROUTE · 14.2 u · min clearance 0.31 u · 0 collisions`**. Plus badges: `SYNTHETIC DATA` (always, the pack is synthetic) and `DEMO MODE · CACHED` when the toggle is on. |

Status mapping `[HYPOTHESIS]`: `healthy → OK` (green), `watch → WATCH` (yellow), `degraded → WATCH` with label `DEGRADED` (yellow), `attention_required → ALERT` (red), unmapped context object → `UNKNOWN` (grey). Theme: `design/cyberpunk-tokens.css`.

---

## 3. MoSCoW requirements

Hours are single-owner estimates `[HYPOTHESIS]` for a 3–4 person team; with 2 people, cut S-items first, never M-items. Owners: **PM** (pitch, data, video), **CV** (geometry pipeline), **AI** (metadata, copilot), **FE** (three.js, curator, XR).

### MUST — the demo fails without it

| ID | Requirement | Acceptance test (binary) | Owner | Est. h |
|---|---|---|---|---|
| **M1** | **Clean scan loader.** `pipeline/01_clean.py` reads the 3DGS PLY, keeps gaussians that are finite, inside the room bounds (`\|x,y,z\| < 20 u`, not within 1 mm of the origin), opacity ≥ 0.05, sane scale; writes `data/derived/clean.npz` (xyz, rgb from `f_dc`, opacity, scale) and `scene_points.bin` (Float32 xyz + Uint8 rgb) | Runs in < 2 min on the demo laptop; keeps 350–500 k points; the room is recognisable in the three.js viewer; bounds and up-axis are logged `[SOURCE DATA: y-up, ≈ 8.6 × 4.4 × 2.6 u]` | CV | 3 |
| **M2** | **Floor & walkable grid.** Floor plane fit (RANSAC on y), 2-D occupancy grid at 0.05 u over x–z using points between floor + 0.10 u and floor + 1.90 u, dilated by the agent radius (0.30 u human / 0.35 u robot `[HYPOTHESIS]`); writes `grid.npz` + `walkable.png` | The walkway between the boilers is walkable and every boiler/pipe cell is blocked on the PNG; floor height matches the visual floor within 0.05 u | CV | 4 |
| **M3** | **Object proposal queue.** Remove floor/ceiling/wall planes, cluster the rest (DBSCAN, eps tuned per density; split oversized clusters along their principal axis), compute PCA-oriented bounding boxes, heuristic class guess (vertical cylinder → tank/boiler, horizontal thin cylinder → pipe, box → cabinet/motor, small → valve/sensor) with a confidence; writes `proposals.json` ordered by size × confidence | ≥ 40 proposals; when the top 20 are highlighted one by one, ≥ 15 correspond to a real object as judged by the team; no proposal spans more than one obvious object | CV | 6 |
| **M4** | **Curator web UI — one by one.** Screen A as specified in §2: proposal `k` in red, rest grey, Approve/Reject/Skip/Relabel with keys, `asset_id` suggestion + override, progress counter; writes through the API to `scene_graph.json` | A new team member approves 10 proposals in < 4 min using only the keyboard; `scene_graph.json` has 10 objects with `approved_at` timestamps; reload restores state | FE | 8 |
| **M5** | **Snapshot on every approval.** After each approval the browser renders the central scene with the **new object red** and **every other approved object translucent grey**, from a fixed isometric camera, and saves `snapshots/NNNN_<object_id>[_<tag>].png` via the API | One PNG per approval exists, numbered consecutively; opening any PNG shows exactly one red object; the last PNG shows all approved objects in grey except the newest | FE | 2 |
| **M6** | **Scene graph + xlsx binding + target fault.** `pipeline/05_bind_metadata.py` loads all 16 sheets into JSON; each approved object may bind to one `Asset_Master` row (procedural suggestion by class, human override in M4); unbound objects are `context` objects; `Scene_Anchors` is rewritten with real centres/bounds and `mapping_status: human_approved`; the target is `ASSET-017 · P-005` with `attention_required` `[SOURCE DATA]` | `GET /api/assets/{id}` returns the merged record (master + current state + last 3-day telemetry + events + docs) for every bound object; all 30 xlsx rows are bound once the curator run is complete; `GET /api/scene/anchors` shows updated coordinates and `mapping_confidence: 1.0` for approved objects | AI | 3 |
| **M7** | **Route planner with clearance.** A* on the dilated grid from the start pose to the nearest walkable cell beside the target object, path smoothing (string-pulling), reported length and minimum clearance; writes `route.json` | Zero route cells are blocked; min clearance ≥ 0.25 u; the route is found in < 1 s; the three sample targets all return a route | CV | 4 |
| **M8** | **Twin: avatar auto-walk + proximity display.** Avatar/robot follows `route.json` at ~1.2 u/s; assets within 1.5 u are highlighted with their status chip and two metadata fields; arrival triggers M9 | In a 60 s run every bound asset within 1.5 u of the path is highlighted exactly while in range; the avatar never intersects a blocked cell; the diagnosis card appears on arrival | FE | 6 |
| **M9** | **Grounded copilot at the target.** `POST /api/copilot/query` builds context from `Current_State`, the last 3-day telemetry of that asset, its events, maintenance history, the class core doc, `DOC-FIELD-SAFETY` and `DOC-RAG-GUIDE`; returns a structured `Diagnosis` JSON with `evidence_ids[]`, `confidence`, `next_safe_check`, `safety_note`; a server-side validator rejects any cited ID that is not in the retrieved set | For all three sample targets the answer cites ≥ 3 existing evidence IDs, names the asset tag, states confidence, separates observation from hypothesis, and arrives in < 8 s (or instantly in Demo Mode) | AI | 6 |
| **M10** | **Walk mode (first-person).** PointerLock + WASD on desktop, collision against the same occupancy grid, eye height = floor + 1.6 u `[HYPOTHESIS]` | The tester cannot pass through a boiler cell; can walk the full route by hand; FPS ≥ 30 on the demo laptop | FE | 3 |
| **M11** | **Demo Mode toggle.** `DEMO_MODE=1` serves pre-computed `Diagnosis` JSON for the three sample targets from `data/cache/`, and the route/proximity run uses the committed artifacts; badge `DEMO MODE · CACHED` shows | Full judge flow runs with Wi-Fi off; outputs are byte-identical across two runs | AI | 2 |
| **M12** | **Submission package** `[SOURCE DATA — brief §07]`: runnable demo, repo README with setup, **5–8 slides**, **video ≤ 5 min**, technical note (models, libraries, components) | All five items exist in `docs/` and the submission form by Sun 09:15; the video shows curator → snapshots → walk → diagnosis → VR | PM | 6 |

**MUST total ≈ 53 h.**

### SHOULD — turns a pass into a win

| ID | Requirement | Acceptance test | Owner | Est. h |
|---|---|---|---|---|
| **S1** | **VLM auto-labels.** For each proposal, render a crop (top + side views of its points over the room) and ask a vision model for `label`, `class ∈ {CONTROL_VALVE, PROCESS_PUMP, ELECTRIC_MOTOR, PRESSURE_TRANSMITTER, VIBRATION_SENSOR, pipe, tank, boiler, cabinet, structure, other}`, `confidence`; results pre-fill the curator | ≥ 60 % of approved objects keep the suggested label unchanged; batch of 150 proposals labelled in < 10 min | AI | 4 |
| **S2** | **Per-object meshes.** Convex hull (or alpha shape) per approved object as `.glb`; the central scene and snapshots use meshes instead of boxes | Snapshot shows the object silhouette, not just a box; total mesh payload < 20 MB | CV | 3 |
| **S3** | **WebXR on Meta Quest 3.** `renderer.xr.enabled`, `VRButton`, thumbstick smooth locomotion on the grid + snap turn, point budget ≤ 300 k, served over HTTPS (or `adb reverse` to `localhost`) | On the headset: enters VR, 72 fps, can walk to `P-005`, status labels readable; exit returns to the desktop view cleanly | FE | 5 |
| **S4** | **Gaussian-splat rendering in Twin mode** (e.g. a three.js splat renderer) with automatic fallback to points when FPS < 30 | The room looks photoreal on the laptop; fallback triggers on the Quest | FE | 4 |
| **S5** | **Merge / split in the curator** (`M` merges with the previous proposal, `X` splits along the principal axis) | A pipe wrongly split into two proposals can be merged in one keystroke | FE | 3 |
| **S6** | **Copilot commentary along the route**: one-line status explanation for each asset entering the proximity ring, cached per asset `[SOURCE DATA — brief §06 c3 "explain device status along the path"]` | Each highlighted asset shows a one-line reason with ≥ 1 evidence ID | AI | 2 |
| **S7** | **Snapshot timelapse** auto-built from `snapshots/` (ffmpeg, 6 fps) for the video and the slides | `docs/timelapse.mp4` exists and plays all snapshots in order | PM | 1 |

### COULD — only after Gate 3 is green

| ID | Requirement | Owner | Est. h |
|---|---|---|---|
| **C1** | `POST /api/work-orders/draft` from a `Diagnosis` (pack's `API_Contract`, draft only, no control actions `[SOURCE DATA]`) | AI | 2 |
| **C2** | Export the scene graph as glTF (boxes + labels) and as a flat OpenUSD-friendly JSON (`Public_Research` rows 9–10) | CV | 2 |
| **C3** | Telemetry replay: scrub the 3-day sample and watch health chips change | FE | 3 |
| **C4** | Rust port of the clustering step (brief invites Python **or** Rust) | CV | 4 |
| **C5** | Remote-expert evidence pack: zip of snapshots + diagnosis + telemetry window (`Builder_Questions` Q-10) | AI | 2 |

### WON'T — the anti-scope list (say it out loud at the stand)

Mobile/Android app (brief says don't) · real OPC UA / MQTT / HART connectivity · any autonomous control action (`DOC-FIELD-SAFETY`) · training a segmentation network · multi-user curation, auth, accounts · photoreal mesh reconstruction of the whole room · robot physics / ROS / Isaac Sim · live SLAM or new scanning · multi-floor navigation and stairs · localisation of the UI · a pretty landing page.

---

## 4. Traceability

| Req | Source data reference | Judging criterion `[SOURCE DATA — brief §06]` | Video moment (≤ 3:30 cut, core in the first 2:00) |
|---|---|---|---|
| M1 | PLY: 1,506,136 gaussians, 67 % unusable (measured); brief §02 "raw 3D captures are semantically blind" | c4 Backend architecture (15 %) | 0:00–0:15 hook: raw splat noise → clean room |
| M2, M7, M10 | brief §02 item 3 "logical, real-world walkable route … avoid walls, boilers, piping"; §04 "occupancy grids … A*" | c2 Navigation (25 %) | 1:05–1:40 route draws, avatar walks; 2:00–2:25 first-person walk hits a boiler and stops |
| M3, M4, M5 | brief §02 item 1 "extract and 3D-frame assets (the more, the better)"; demo videos "Every object, its own asset"; `DOC-3D-MAPPING` "never silently guess identity" | c1 Extraction density & framing (30 %) | 0:15–0:45 curator montage + snapshot timelapse, counter climbing |
| M6 | brief §02 item 2 "map synthetic metadata … random or procedural is acceptable"; `Scene_Anchors.remap_instruction` | c1 (mapping) + c3 | 0:45–1:05 status chips appear, `P-005` turns `ALERT` |
| M8, S6 | brief §02 item 4 "all extracted assets near the robot are dynamically highlighted … mapped metadata/status displayed" | c2 Proximity display | 1:05–1:40 proximity ring highlights assets |
| M9 | brief §02 item 4 "AI assistant diagnoses the condition and recommends next inspection/service steps"; `DOC-RAG-GUIDE`; `Builder_Questions` Q-03, Q-06 | c3 AI diagnostics & grounding (20 %) | 1:40–2:00 diagnosis card with evidence IDs |
| M11 | brief §06 "demonstrated reliably" | c5 Demo clarity (10 %) | whole video runs in Demo Mode |
| M12 | brief §07 submission package | all | 2:40–3:10 architecture slide; 3:10–3:30 close |
| S3, S4 | brief §04 "lightweight visualization … Three.js/Web, Unity, Unreal"; `START_HERE` interoperability row | c5 Innovation | 2:25–2:40 Quest 3 clip |
| S1 | brief §04 "multi-view vision foundation models like SAM/CLIP lifted to 3D" | c1 | 0:30 label suggestions visible in the curator |
| C1 | `API_Contract` `POST /api/work-orders/draft` | c3 | optional 1:55 "Draft work order" tap |

---

## 5. Data contracts (summary — full schemas in `06_AGENTS_Master_Context.md`)

`Proposal` → `ApprovedObject` → `SceneGraph` (the "central mesh") → `AssetRecord` (xlsx merge) → `Route` → `Diagnosis`. Every object carries `object_id`, `obb`, `label`, `class_guess`, `confidence_auto`, `asset_id | null`, `mapping_confidence`, `snapshot_uri`. The three.js app never computes geometry; it only renders what the pipeline wrote.

## 6. Open questions that change this document

G1 scale/up-axis, G2 cleaner export or camera poses, G4 what counts as an asset and whether human-approved extraction scores fully, G5 target choice and start pose, G6 GPU/cloud/public-repo permissions, G7 judging mechanics — all in `01_Partner_Briefing_Questions.md`. Update the MoSCoW hours after the first mentoring window.
