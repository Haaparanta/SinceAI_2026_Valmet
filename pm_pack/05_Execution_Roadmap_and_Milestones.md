`// VALMET × SINCE AI 2026 · PM PACK · 05`

# 05 — Execution Roadmap & Milestones

Ten four-hour sprints, five binary gates, one approval run, one Sunday run-sheet — from a dirty splat on Friday night to a walkable, human-verified twin on Sunday morning.

`v1.0.0 · GENERATED 2026-11-06 20:45 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data; the question lives in `01_Partner_Briefing_Questions.md`. `[HYPOTHESIS]` = our deduction or design choice. Team roles are slots (**PM / CV / AI / FE**) because the team composition was not given; map them to names on Friday night.

> [!WARNING]
> **The clock already started.** The build window is Fri 19:30 → Sun 10:00 EET `[SOURCE DATA — README]`; this document was generated at ~20:45 on Friday, so Sprint 1 is already running with ~2 h 45 min left. Requirement IDs (`M1`–`M12`, `S1`–`S7`, `C1`–`C5`) and gap IDs (`G1`–`G8`) are those of `02_Requirements_Management_PRD.md`. Kill/pivot gates are written **Gate 1 … Gate 5** so they never collide with gap IDs, and sprints are written `SP1`–`SP10` so they never collide with SHOULD IDs.

---

## 1. Sprint plan — Fri 19:30 → Sun 10:00

Lanes: **PM** (pitch, data, video, curation), **CV** (geometry pipeline), **AI** (metadata, copilot, demo cache), **FE** (three.js, curator, XR). Hours per item are the estimates from `02 §3` `[HYPOTHESIS]`.

| Sprint | Window (EET) | PM | CV | AI | FE | Exit criterion (binary) | Who sleeps |
|---|---|---|---|---|---|---|---|
| **SP1** | Fri 19:30–23:30 *(in progress)* | First-90-minutes checklist (§6); post first questions in Discord; assign owners | **M1** clean loader → `clean.npz`, `scene_points.bin` | **M6** xlsx → JSON (all 16 sheets); evidence-ID conventions | Vite + TS + three.js scaffold; renders `scene_points.bin` | Room visible in the browser from the cleaned file; all sheets load | nobody |
| **SP2** | Fri 23:30–Sat 03:30 | Scene-unit sanity check vs floor height; draft slide skeleton; sleep from 01:00 | **M2** floor + walkable grid PNG; start **M3** clustering | **M6** finish; `AssetRecord` merge; start **M9** retrieval context; sleep from 01:00 | **M4** curator skeleton: proposal list, red/grey rendering, keyboard | **Gate 1 at 00:30** | PM + AI 01:00–06:00 |
| **SP3** | Sat 03:30–07:30 | *(asleep → 06:00)* then review Gate 1 output, prep mentoring questions | **M3** proposals ≥ 40, OBBs, heuristic labels; sleep from 04:00 | *(asleep → 06:00)* then **M9** prompt + citation validator | **M4** approve/reject/relabel wired to API; **M5** snapshot; sleep from 04:00 | `proposals.json` with ≥ 40 entries; first snapshot PNG on disk | CV + FE 04:00–08:30 |
| **SP4** | Sat 07:30–11:30 | **Approval run pass 1** (§3) from 08:45; first mentoring window `[GAP - ASK PARTNER]` — show the ugly prototype | *(asleep → 08:30)* then **M7** A* with clearance | **M9** end-to-end on `P-005`; **M11** cache skeleton | *(asleep → 08:30)* then **M8** avatar follows `route.json` | **Gate 2 at 08:30**; ≥ 10 approved + bound; partner feedback captured in the briefing card | — |
| **SP5** | Sat 11:30–15:30 | **Approval run pass 2**; re-score risks after partner answers; update `01b` card | **M7** done for all three targets; start **S2** per-object meshes | **S1** VLM labels batch for remaining proposals; **S6** along-route one-liners | **M8** proximity ring + chips; **M10** walk mode collision | Route for all 3 targets; walk mode cannot cross a boiler | — |
| **SP6** | Sat 15:30–19:30 | **Approval run pass 3** with VLM labels; video shot list locked | **S2** meshes into snapshots; `walkable.png` overlay for slides | **M9** all three targets cited and validated; **M11** three cached answers | **M8** arrival → diagnosis card; status bar proof metrics | **Gate 3 at 16:30** | — |
| **SP7** | Sat 19:30–23:30 | Architecture slide; README draft; `brew install ffmpeg`; **S7** timelapse | **C2** glTF export (only if Gate 3 green); bug bash on grid edge cases | Demo-mode byte-identical check; **C1** work-order draft if time | **S3** WebXR on Quest 3 (HTTPS or `adb reverse`); **S4** splat renderer try (fallback to points) | Full flow runs on one laptop with Wi-Fi off once | — |
| **SP8** | Sat 23:30–Sun 03:30 | Record video takes (screen capture at 1080p); sleep from 02:00 | Fix anything Gate 4 flagged; sleep from 02:00 | Final cached answers frozen; sleep from 00:30 | VR go/no-go by 00:30; polish only after Gate 4; sleep from 00:30 | **Gate 4 at 00:30**; ≥ 60 approved objects | AI + FE 00:30–04:30, PM + CV 02:00–06:00 |
| **SP9** | Sun 03:30–07:30 | *(asleep → 06:00)* then video edit + export, slides final | *(asleep → 06:00)* then technical note (models, libraries, components) | *(awake 04:30)* README setup steps verified on a clean clone | *(awake 04:30)* demo machine prep, rehearsal #1 Wi-Fi off | **Gate 5 at 06:30** | see SP8 |
| **SP10** | Sun 07:30–10:00 | Submission form by **09:15**; stand script rehearsal | Code freeze **08:00**; tag `v1.0-submission` | Rehearsal #2 Wi-Fi off; cache integrity check | Headset charged, HTTPS/`adb reverse` verified, laptop on power | Submitted with 45 min buffer; two clean rehearsals logged | — |

**Sleep plan** `[HYPOTHESIS]`: night owls (CV, FE) push through Friday night and sleep 04:00–08:30; early birds (PM, AI) sleep 01:00–06:00. On Saturday night the pairs swap: AI + FE sleep 00:30–04:30, PM + CV sleep 02:00–06:00. Everyone gets ≥ 8.5 h across the two nights; nobody is awake for more than 22 h in a row.

**Two-person variant** `[HYPOTHESIS]`: Person A = CV + AI (pipeline, metadata, copilot), Person B = FE + PM (curator, twin, video). Keep every `M` item; drop `S4`, `S5`, `C1`–`C5`; attempt `S3` only if Gate 4 passes with ≥ 2 h spare; `S1` only if the VLM call is a 30-minute job. Curation is done by both in alternating 20-minute blocks during SP4–SP6. Sleep: A 02:00–06:30 and 01:00–05:00, B 04:00–08:30 and 00:30–04:30.

**Mentoring windows** `[GAP - ASK PARTNER]`: the brief promises Valmet representatives "during the agreed mentoring windows" on the Since AI Discord `[SOURCE DATA — brief §08]` but gives no times. Assume one Saturday-morning and one Saturday-afternoon slot; confirm on Discord tonight and move the Gate 2 demo to the first slot.

---

## 2. Kill / Pivot gates

Every gate is a 15-minute standing meeting with one owner, one binary PASS test and one pre-agreed action. No discussion beyond 15 minutes: the owner decides.

| Gate | When | PASS test (binary, observable) | KILL / PIVOT if it fails | Owner |
|---|---|---|---|---|
| **Gate 1** | Sat 00:30 | (a) the cleaned room renders in the three.js scaffold from `scene_points.bin`; (b) `walkable.png` exists and the corridor between the boilers is white while boiler cells are black; (c) `proposals.json` has ≥ 40 entries with OBBs | If clustering is garbage: switch `M3` to **voxel-blob proposals** (0.25 u voxel occupancy → connected components) and add a **manual box tool** to the curator so a human can draw the first 30 objects. If (b) fails: lower the slab (floor + 0.05 … + 1.5 u) and re-run; if still wrong, hand-mark the floor polygon | CV |
| **Gate 2** | Sat 08:30 | (a) one keystroke approves a proposal, the object appears in `scene_graph.json`, and a numbered PNG lands in `data/snapshots/` with the new object red and the rest translucent grey; (b) ≥ 10 approved objects are bound to xlsx assets and `GET /api/assets/ASSET-017` returns the merged record; (c) the ugly prototype can be screen-shared at the first mentoring window | If the curator is slow or flaky: **OBB-only mode** (no per-object meshes, no auto-framing), keyboard only, snapshots rendered from boxes. If binding is the blocker: procedural binding by class order, human override later | FE |
| **Gate 3** | Sat 16:30 | (a) `route.json` for all three targets with zero blocked cells and min clearance ≥ 0.25 u; (b) the avatar walks `P-005` without entering a blocked cell and the proximity ring highlights assets; (c) walk mode stops at a boiler; (d) `POST /api/copilot/query` returns a `Diagnosis` whose every `evidence_id` passes the validator for all three targets | If the route clips: raise the dilation radius by 0.05 u steps; if still clipping, fall back to **hand-verified waypoints** stored in `route.json` with `planner: "manual_verified"` and say so on screen. If the copilot fails validation: shrink the context to `Current_State` + events + core doc, retry; if still failing, serve only cached answers (`M11`) and label them `CACHED` | CV (route), AI (copilot) |
| **Gate 4** | Sun 00:30 | (a) the full judge flow (pick target → route → walk → arrival → diagnosis) runs on one laptop with Wi-Fi off in Demo Mode, twice, with identical output; (b) ≥ 60 approved objects in `scene_graph.json`, all 30 xlsx assets bound; (c) VR go/no-go: the scene enters VR on the Quest 3 at ≥ 60 fps and the tester reaches `P-005` | VR no-go → drop `S3`, remove the VR button, and describe the architecture as "VR-ready" **only** if the WebXR code path exists and was tested on a desktop emulator; never show a staged VR clip. If (a) fails: freeze features, fix the flow, nothing else is allowed in | PM (flow), FE (VR) |
| **Gate 5** | Sun 06:30 | (a) `docs/video.mp4` ≤ 5 min exported; (b) 5–8 slides exported to PDF; (c) README with setup steps verified on a clean clone; (d) technical note lists every model, library and component `[SOURCE DATA — brief §07]` | Anything missing → the PM writes it from the shot list and the AGENTS file; the demo video is replaced by the raw screen capture from SP8 if the edit is not done by 07:30. **Code freeze 08:00. Submit by 09:15. Buffer 45 min** | PM |

---

## 3. The approval run (Saturday)

The curator (`M4`) is where criterion 1 (30 %) is earned. Proposals come from `M3`; a human turns them into approved objects one at a time; each approval produces a snapshot (`M5`) `[SOURCE DATA — your five non-negotiables]`.

| Pass | When | Who | Target | Notes |
|---|---|---|---|---|
| 1 | Sat 08:45–10:00 | CV (knows the clusters) + PM | 30 approved | Largest proposals first; bind the obvious ones to xlsx assets by class (`P-005` → the pump nearest the back wall `[HYPOTHESIS]`) |
| 2 | Sat 12:00–13:30 | PM | +25 | After `M7` routes exist: prioritise objects within 1.5 u of the three routes so the proximity ring has things to show |
| 3 | Sat 16:30–18:00 | PM + AI | +25, stretch to 120 total | With `S1` VLM labels pre-filled; use `S5` merge/split if it landed |

**Keyboard flow:** `A` approve · `R` reject · `S` skip · `L` relabel (focus label) · `M` merge with previous (`S5`) · `X` split (`S5`) · `↑/↓` change suggested `asset_id` · `Enter` confirm. Target cadence: ≤ 15 s per decision → 100 decisions in 25 minutes.

**Counts:** ≥ 60 approved objects by Gate 4 (`M4` acceptance), all 30 `Asset_Master` rows bound exactly once `[SOURCE DATA — 30 assets]`, remaining approvals are `context` objects (pipes, cabinets, structure). The status bar shows the honest split: `87 approved · 30 bound · 57 context`.

> [!CAUTION]
> **Approve only what you would defend to Mika.** Mika Karaila is the Valmet point of contact `[SOURCE DATA — brief §08]`. If a proposal is half a pipe and half a wall, reject it or split it. A smaller honest count beats a larger padded one — the judges will ask what a frame contains.

---

## 4. Sunday run-sheet (06:30 → pitch)

| Time | Action | Owner | Done when |
|---|---|---|---|
| 06:30 | **Gate 5** | PM | all five PASS items ticked |
| 06:30–07:30 | Video final edit + export (`docs/video.mp4`, ≤ 5 min, 1080p) | PM | file plays start to end, length checked |
| 06:30–07:30 | Technical note (`docs/technical_note.md`): models, libraries, components, data filters, numbers | CV | every number traceable to `data/derived/` |
| 07:00–07:45 | README setup steps re-run on a clean clone (`uv sync`, `npm ci`, `make demo`) | AI | demo opens in < 5 min from clone |
| 07:30–08:00 | Slides 5–8 → PDF; shot list reconciled with the video | PM | PDF exported |
| **08:00** | **Code freeze**, tag `v1.0-submission`, push | CV | tag visible on GitHub |
| 08:00–08:30 | Demo machine prep: Wi-Fi **off**, `DEMO_MODE=1`, cache integrity check, laptop on mains, display scaling set, browser kiosk window | FE | checklist signed |
| 08:30–08:50 | **Rehearsal #1** (Wi-Fi off, full flow, stopwatch) | all | flow < 3 min, no errors |
| 08:50–09:10 | Headset: charged ≥ 80 %, HTTPS cert or `adb reverse tcp:5173 tcp:5173` verified, VR entry tested once | FE | enters VR, reaches `P-005` |
| **09:15** | **Submit** (repo URL, video, slides PDF, technical note) on the Since AI submission form | PM | confirmation received |
| 09:15–09:45 | **Rehearsal #2** with the 3-minute stand script | all | timed ≤ 3 min |
| 09:45–10:00 | Buffer. Nothing new. | — | — |
| after 10:00 | Peer voting / stage finals / jury walk-through `[GAP - ASK ORGANIZER]` — Since AI's exact format is not in the source data; confirm slot times, whether the Valmet jury sees a live demo or the video, and whether a headset may be used on stage | PM | schedule pinned in Discord |

### 3-minute stand script `[HYPOTHESIS]`

1. **0:00** "This is Valmet's boiler room — 1.5 million gaussians, two thirds of them noise, and zero meaning. We gave it meaning one object at a time." *(show raw vs clean)*
2. **0:25** "Our pipeline proposes objects offline; a human approves each one in the web — and every approval takes a photo: the new object red, everything else grey." *(timelapse, counter climbing to the real number)*
3. **1:00** "Each approved object binds to Valmet's synthetic asset data. `P-005` is fouling, health 44." *(status chips)*
4. **1:20** "Press *Walk to P-005*. The route is planned on an occupancy grid with clearance — the avatar never clips through a boiler, and nearby assets light up with their status." *(auto-walk)*
5. **1:55** "At the pump, the copilot explains why, citing the exact telemetry window, event IDs and guidance docs — and it refuses to invent an ID." *(diagnosis card)*
6. **2:20** "Same scene, first person — and on the Quest 3." *(walk; headset if go)*
7. **2:45** "Everything you saw is reproducible from `data/derived/`. Questions?"

### Video shot list (≤ 5 min; cut at ~3:30) — consistent with `02 §4`

| Time | Shot | Source |
|---|---|---|
| 0:00–0:15 | Hook: raw splat noise → cleaned room (`M1`) | screen capture, viewer |
| 0:15–0:45 | Curator timelapse: approvals one by one, snapshots, counter climbing (`M3`–`M5`, `S7`) | `docs/timelapse.mp4` |
| 0:45–1:05 | Binding: status chips appear, `P-005` turns `ALERT` (`M6`) | twin |
| 1:05–1:40 | Route draws, avatar walks, proximity ring highlights (`M7`, `M8`) | twin |
| 1:40–2:00 | Arrival: diagnosis card with evidence IDs (`M9`) | twin |
| 2:00–2:25 | First-person walk, stops at a boiler (`M10`) | twin |
| 2:25–2:40 | Quest 3 clip (`S3`) — **only if Gate 4 VR = go** | headset capture |
| 2:40–3:10 | Architecture: offline pipeline → API → three.js; honest metrics (`M11`, `M12`) | slide |
| 3:10–3:30 | Close: what Valmet gets on Monday; the robot gets the same route as JSON | slide |

### Honesty checklist (tick before Gate 5)

- [ ] Every number on screen or in slides (`approved`, `bound`, route length, clearance, confidence) is read from `data/derived/` or `scene_graph.json`, never typed in
- [ ] The asset counter shows the real `scene_graph.json` count, including the honest `context` split
- [ ] Every diagnosis shown cites only IDs that exist in the xlsx (validator log attached in `docs/`)
- [ ] `SYNTHETIC DATA` badge visible in every twin shot; `DEMO MODE · CACHED` visible whenever the cache served the answer
- [ ] No VR footage unless recorded on the headset during Gate 4
- [ ] The technical note lists every model and library actually used, including the VLM/LLM model IDs
- [ ] Scale is reported in "scene units" until `G1` is answered

---

## 5. First 90 minutes (tonight, from ~20:45)

- [ ] `uv python install 3.12 && uv venv --python 3.12`, then the `uv pip install …` line from `06 §1` — Python 3.15 has no numpy/open3d wheels on this Mac `[HYPOTHESIS]`
- [ ] `ln -s ../Source-Data-Do-Not_change data/raw` — never modify the raw folder; `.ply`/`.mp4` are gitignored `[SOURCE DATA — .gitignore]`
- [ ] `uv run python pipeline/01_clean.py` → `data/derived/clean.npz`, `scene_points.bin`; log kept count and bounds (expect ≈ 400–500 k points, y-up, ≈ 8.6 × 4.4 × 2.6 u)
- [ ] `uv run python pipeline/05_bind_metadata.py --dump` → `data/derived/xlsx/*.json` for all 16 sheets
- [ ] `npm create vite@latest web -- --template vanilla-ts && npm i three` → render `scene_points.bin` as `THREE.Points`
- [ ] Agree the contracts in `06_AGENTS_Master_Context.md` (field names frozen; changes only via `docs/CONTRACT_CHANGES.md`)
- [ ] Assign PM / CV / AI / FE names; pick the night owls
- [ ] Post the Top 5 questions from `01_Partner_Briefing_Questions.md` in the Since AI Discord challenge channel `[SOURCE DATA — brief §08]`; ask for the mentoring-window times
- [ ] `brew install ffmpeg` in the background (needed for `S7` and the video)
- [ ] Charge the Quest 3; confirm `adb` sees it (`adb devices`) for `S3`
