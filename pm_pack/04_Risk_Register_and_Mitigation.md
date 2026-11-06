`// VALMET × SINCE AI 2026 · PM PACK · 04`

# 04 — Risk Register & Mitigation

Fifteen scored risks with observable triggers and concrete fallbacks, the Cached Demo Mode toggle, and the kill/pivot ladder that protects the four non-negotiables.

`v1.0.0 · GENERATED 2026-11-06 20:45 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data; the question lives in `01_Partner_Briefing_Questions.md`. `[HYPOTHESIS]` = our deduction or design choice. Team roles are slots (**PM / CV / AI / FE**) because the team composition was not given; map them to names on Friday night.

> [!WARNING]
> Likelihood and impact were scored at Fri 20:45 EET, **before** the first mentoring window, with an unknown team and no GPU confirmed. Re-score at every gate (see §4). Scale: **L** = likelihood 1–5, **I** = impact 1–5, **Score** = L × I; anything ≥ 15 is reviewed at every stand-up.

---

## 1. Risk register

| ID | RISK | L | I | SCORE | TRIGGER (OBSERVABLE) | OWNER | HARD FALLBACK | RE-SCORE AT |
|---|---|---|---|---|---|---|---|---|
| **R1** | **PLY dirtier than the 67 % measured.** `[SOURCE DATA]` 844 k gaussians beyond ±100 u, 11 k NaN, 150 k near-transparent, ~20 % of the rest collapsed at the origin — and the surviving ~400 k may still carry floaters that make DBSCAN return one giant blob or hundreds of specks. | 4 | 5 | **20** | After `pipeline/01_clean.py` + `03_propose.py`, the top-20 proposals contain < 10 real objects, or one cluster holds > 40 % of points | CV | Tighten `01_clean.py` filters (opacity ≥ 0.15, max-axis scale ≤ 0.5 u, statistical outlier removal k = 20 / σ = 2); voxel-downsample to 0.02 u before clustering; if still bad by Gate 1, switch `03_propose.py` to **voxel-grid connected components** at 0.1 u and let the curator (`M4`) do the splitting with `S5`. Never spend more than 2 h here — approval absorbs noise. | Gate 1 |
| **R2** | **Scale / up-axis wrong.** Measured y-up, floor ≈ y −0.9, room ≈ 8.6 × 4.4 × 2.6 u `[SOURCE DATA]`; metric scale is `[GAP - ASK PARTNER]` G1. A 2.6 u ceiling is low for a boiler room → 1 u may be ≈ 1.3–1.5 m. | 3 | 4 | 12 | Partner answer to G1, or the avatar (1.6 u eyes) looks like a giant / a child next to the boilers | CV | All constants live in `pipeline/config.py` as `UNITS_PER_METRE` and `UP_AXIS`; clearance, eye height, proximity radius, walking speed and grid resolution are derived from them — one edit, re-run `02_floor_grid.py` and `06_route.py` (< 5 min). Until confirmed the UI says **units**, not metres. | Gate 2 |
| **R3** | **Referenced data missing.** `telemetry_full_14d_30min.csv` and the 38 `DOC-*.md` RAG files are referenced in `START_HERE` / `RAG_Corpus_Index` but not in the package `[SOURCE DATA]`. | 4 | 2 | 8 | Not received from the partner by the first mentoring window (G3) | AI | `05_bind_metadata.py` already builds the RAG corpus from what exists: the 8 inline `Knowledge_Docs` plus a generated **asset card** per `Asset_Master` row (master + current state + last events + maintenance history). The 3-day `Telemetry_Sample_3d` is enough for the diagnosis window. If the files arrive, drop them into `data/raw/` and re-run — same doc IDs. | Gate 2 |
| **R4** | **NDA / public-repo / cloud-LLM restrictions** `[GAP - ASK PARTNER]` G6: the PLY may not be publishable, frames may not go to a cloud VLM, the video may not show the room. | 2 | 4 | 8 | Partner says "no cloud", "no public footage" or "no redistribution of the PLY" | AI | `LLMClient` has a local backend (Ollama) behind the same interface; `S1` VLM labels are skipped (curator labels by hand); public repo ships code + xlsx-derived JSON only, `data/raw/` stays `.gitignore`d (already is for `*.ply`, `*.mp4` `[SOURCE DATA]`); video uses the synthetic metadata overlay and, if required, the grey point render instead of the splat. | Gate 2 |
| **R5** | **Human-in-the-loop judged as "not automated".** Criterion 1 says "process … to extract" and criterion 4 says "automated" `[SOURCE DATA — brief §02, §06]`; a judge may score the approved count as manual labelling `[GAP - ASK PARTNER]` G4. | 3 | 5 | **15** | Partner reaction at the first mentoring window, or the G4 answer is "fully automatic only" | PM | The status bar shows **two numbers**: `AUTO · 137 proposals` and `APPROVED · 87`, and the pipeline can run with `--auto-approve --min-confidence 0.7` to produce a fully automatic scene graph for comparison (same JSON, `approved_by: "pipeline"`). Pitch line in `03` §3. If the partner insists, the demo opens in auto mode and the curator becomes the "quality step" slide. | Gate 2 |
| **R6** | **Proposal quality too low / over-segmentation** — pipes split into dozens of segments, boilers merged with their piping. | 4 | 3 | 12 | > 50 % of proposals rejected in the first 30 curator decisions | CV | Two-pass clustering (coarse eps 0.15 u, then split clusters larger than 2 u along the principal axis); `S5` merge/split keys in the curator; minimum proposal size 500 points; proposals ordered by size × confidence so the big obvious objects are approved first and the long tail is skipped at Gate 4. | Gate 1, Gate 3 |
| **R7** | **Curator throughput and approval fatigue.** 150 proposals × 15 s ≈ 38 min per full pass; relabelling by hand doubles it. | 3 | 3 | 9 | Fewer than 40 approvals per hour of curator time, or the curator session is interrupted and state is lost | FE | Keyboard-first (`A`/`R`/`S`/`L`), `S1` pre-filled labels, auto-suggested `asset_id`, state in `scene_graph.json` after every decision (reload restores), two curators in shifts (PM + AI) while CV/FE build. Hard floor: **≥ 60 approved** by Gate 4; the 30 xlsx-bound assets come first. | Gate 2, Gate 4 |
| **R8** | **Snapshot capture pitfalls** (`M5`): `canvas.toDataURL()` returns black without `preserveDrawingBuffer: true` or when called outside the render; camera drift breaks the timelapse; async save loses numbering. | 3 | 3 | 9 | First snapshot is black / empty, or PNG numbering has gaps | FE | `WebGLRenderer({ preserveDrawingBuffer: true })` in curator mode only; render the snapshot scene synchronously (`renderer.render(snapshotScene, isoCamera)` then `toDataURL`) from a **fixed isometric camera stored in `scene_graph.json`**; the server assigns `NNNN` from the object sequence, not the request order; fallback is a headless Python render of boxes with matplotlib if WebGL fails on the laptop. | Gate 2 |
| **R9** | **three.js performance on the demo laptop** — 400 k points + meshes + labels + route in Walk mode drops below 30 fps; `S4` splat rendering is heavier still. | 3 | 4 | 12 | FPS < 30 in Walk mode on the actual demo machine | FE | Point budget via `POINT_BUDGET` env (default 300 k, Quest 150 k); `THREE.Points` with a single material; labels as sprites only within the proximity ring; `S4` auto-falls back to points when FPS < 30 for 3 s; rehearse on the demo machine, not the dev machine. | Gate 3 |
| **R10** | **WebXR on Meta Quest 3** (`S3`): WebXR needs a secure context; the headset cannot reach the laptop's `http://` dev server; 72 fps budget; controller locomotion untested. | 4 | 2 | 8 | Headset shows no "Enter VR" button, or the session drops below 60 fps, or no working headset by Sat 22:00 | FE | Order of attempts: (1) **`adb reverse tcp:5173 tcp:5173`** — `localhost` is a secure context on the Quest browser `[HYPOTHESIS]`; (2) `mkcert` HTTPS on the LAN; (3) a Cloudflare/ngrok tunnel. Point budget 150 k, no labels outside the ring, snap turn + thumbstick walk on the grid. **Explicit go/no-go at Gate 4 (Sun 00:30):** no VR after that point — the video shows a desktop walk and VR is mentioned as "WebXR-ready, not demoed". Never let VR eat MUST hours. | Gate 4 |
| **R11** | **LLM latency, outage or hallucination** (`M9`): > 8 s answers, 429s on venue Wi-Fi, invented evidence IDs. | 3 | 5 | **15** | Any copilot call > 5 s during rehearsal, any cited ID not in the retrieved set, any non-JSON response | AI | Structured output (`Diagnosis` schema) + a **server-side citation validator** (every `evidence_id` must exist in the retrieved context, else the answer is replaced by "Insufficient evidence for a grounded diagnosis — next safe check: verify asset identity"); `DEMO_MODE=1` cache (§2); low-effort setting for latency; local Ollama backend as last resort. | Gate 3, Gate 4 |
| **R12** | **Environment: Python 3.15 wheels / no GPU.** Homebrew Python 3.15.2 has no numpy/open3d; Open3D and torch wheels usually lag new Python versions `[HYPOTHESIS]`; no GPU confirmed `[SOURCE DATA — local tooling]`. | 4 | 3 | 12 | `uv sync` fails on open3d / numpy for > 20 min, or SAM/CLIP cannot run locally | CV | `uv python install 3.12 && uv venv --python 3.12`; CPU-only stack (numpy, scipy, scikit-learn DBSCAN, trimesh/open3d for hulls); the PLY is read with `numpy.fromfile` and the known 59-float record, no `plyfile` needed; VLM labels (`S1`) go through the API, never a local model. | Gate 1 |
| **R13** | **Brief misinterpretation** — judges expect something we did not build (fully automatic extraction, a robot-sim export, a specific target device, a live run rather than a video). | 3 | 5 | **15** | Lukewarm or corrective partner reaction at the first mentoring window | PM | **Mandatory ugly end-to-end prototype shown at the first mentoring window** (clean room + a few approved boxes + a route), with the G4/G5/G7 questions read aloud from `01b_Partner_Briefing_Card.html`; pre-agreed pivot levers: auto-approve mode (R5), target device switch (`config.py`), video-first submission. | Gate 2 |
| **R14** | **Team capacity unknown / burnout.** Hours in `02` assume 3–4 people; a 2-person team or a 05:00 crash breaks the critical path. | 3 | 3 | 9 | A gate missed by > 1 h, or anyone awake > 20 h | PM | Sleep shifts in `05`; cut order in §3 (S → C, never M); CV and FE never sleep at the same time between Gate 1 and Gate 3; the PM protects the curator session (R7) as the one task anyone can do. | every gate |
| **R15** | **Submission logistics** — no `ffmpeg` on the build machine `[SOURCE DATA — local tooling]`, video render, slides export, form upload, repo access. | 2 | 5 | 10 | Video not rendered by Sun 06:30, or the submission form rejects a file | PM | `brew install ffmpeg` on Friday night (needed for `S7` too); record with QuickTime/OBS as the fallback; slides exported to PDF at Gate 4 and again at Gate 5; **FINAL** submission by Sun 09:15 leaving 45 min of buffer; repo README written at Gate 4, not Gate 5. | Gate 4, Gate 5 |

**Heat map:** `R1` (20) · `R5` / `R11` / `R13` (15) are the stand-up risks. `R2` / `R6` / `R9` / `R12` (12) are the Saturday-morning risks. Everything else is monitored at gates.

---

## 2. Cached Demo Mode Toggle (`M11`)

> [!CAUTION]
> The live demo is a MUST, the live LLM is not. Demo Mode is the reason the judges never see a spinner.

| ITEM | SPEC |
|---|---|
| **Switch** | Environment flag `DEMO_MODE=1` on the API, mirrored by a UI toggle in the status bar (`localStorage`-backed, defaults to the env value). Both sides read the same flag through `GET /api/demo-mode`. |
| **What is cached** | `data/cache/diagnosis_ASSET-017.json`, `data/cache/diagnosis_ASSET-024.json`, `data/cache/diagnosis_ASSET-014.json` (the three sample targets `[SOURCE DATA — Current_State attention_required]`); `data/derived/route_<asset_id>.json` for the same three targets; `S6` per-asset one-liners in `data/cache/route_commentary.json`; `S1` proposal labels in `data/derived/proposals.json` (already offline by design). |
| **How it is produced** | `pipeline/07_demo_cache.py` runs the live copilot once per target against the final `scene_graph.json`, passes the citation validator, and writes the JSON with a `cached_at` timestamp and the `scene_graph` hash. The route cache is written by `06_route.py --all-targets`. Re-run after any change to approvals or binding. |
| **Determinism** | With `DEMO_MODE=1` the API never calls the LLM; two consecutive runs must produce **byte-identical** responses and the same route length / clearance numbers on screen. A hash of the three diagnosis files is printed at startup and checked in rehearsal. |
| **Badge** | `DEMO MODE · CACHED` (accent tint) in the status bar while on, next to the permanent `SYNTHETIC DATA` badge. Status is text, not colour only. |
| **Rehearsal rule** | Rehearse the full judge flow **with Wi-Fi off** at Gate 4 and again at Gate 5. Live mode is shown first at the stand **only if the live rehearsal passed twice in a row** on the demo machine; otherwise the demo opens in Demo Mode and live mode is offered as "and here is the same question live" at the end. |
| **Cache miss** | A target not in the cache falls through to the live path if online, else returns the validated "Insufficient evidence" placeholder — never an error dialog. |

---

## 3. Kill / pivot ladder

Cut from the top when a gate is missed; stop cutting when the gate is green again. Each rung names what the demo loses so the trade is explicit.

1. **`S3` WebXR / Quest 3** → the video shows a desktop walk; "WebXR-ready" becomes a slide line. (Go/no-go at Gate 4, no exceptions.)
2. **`S4` splat rendering** → the Twin renders the clean point cloud; still photographic enough from a distance.
3. **`S1` VLM auto-labels** → curators type labels; throughput drops (R7), raise the keyboard shortcuts' priority.
4. **All `C1`–`C5`** → no work-order draft, no glTF/USD export, no telemetry replay, no Rust port, no evidence pack.
5. **`S5` merge/split, `S6` route commentary, `S7` timelapse** → accept some over-segmentation; the proximity ring shows status chips only; the video uses a screen recording of the curator instead of a rendered timelapse.
6. **Reduce the approved-object target** from ≥ 60 to ≥ 30 (the xlsx-bound assets only) → density score drops; the honesty metric still holds.
7. **OBB boxes only** (drop `S2` meshes everywhere, including snapshots) → the red-on-grey snapshot still works; boxes are the fallback by design.

**Never cut, at any gate:** `M4` one-by-one approval, `M5` a snapshot after every approval (new object red, rest see-through grey), `M7` a collision-free route, `M9` a diagnosis that cites real evidence IDs. If any of these four is at risk, the pivot is to **narrow the scene** (curate one half of the room, route within it), not to drop the behaviour.

---

## 4. Risk review cadence

Risks are re-scored at the gates defined in `05_Execution_Roadmap_and_Milestones.md`, by the PM, in under five minutes: **Gate 1 (Sat 00:30)** `R1` `R6` `R12` — is the geometry usable? **Gate 2 (Sat 08:30)** `R2` `R3` `R4` `R5` `R7` `R8` `R13` — did the partner change anything, does the approval loop hold? **Gate 3 (Sat 16:30)** `R6` `R9` `R11` — does the walk and the copilot survive a rehearsal? **Gate 4 (Sun 00:30)** `R7` `R10` `R11` `R15` — VR go/no-go, Demo Mode hash, Wi-Fi-off run. **Gate 5 (Sun 06:30)** `R15` only — ship. `R14` is checked at every gate by asking one question: who has slept?
