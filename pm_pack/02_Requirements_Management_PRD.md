# 02 — Requirements & PRD: "Point, Path, Why" Plant Twin

> ⚠️ **PROVISIONAL: BASED ON MISSING DATA.**
> Generated from `README.md` only. There were no datasets, API docs, NDA terms, evaluation criteria, team size or roles. Personas, baselines, ROI numbers and owners are **placeholders** tagged `[HYPOTHESIS]` until the partner confirms them. Owners use role slots (**PM / CV / AI / FE**). Map them to real names once the team is known.

**Selected wedge:** Wedge 1 `[HYPOTHESIS]`. It is the default; confirm or switch after the briefing.

---

## 1. Monday-morning persona

**Mikko, Valmet field service expert** `[HYPOTHESIS]`. He has been sent to a customer's mill he has visited once, two years ago. An alert says a piece of equipment "needs attention" `[README]`.

### Before (today) `[HYPOTHESIS]`. Baseline numbers are `[GAP - ASK PARTNER]` (Q11)

| Step | Today | Est. time |
|---|---|---|
| 1 | Reads the alert, then looks up the asset ID in the maintenance system | ~5 min |
| 2 | Searches manuals, P&IDs and past work orders across several systems ("fragmented technical data" `[README]`) | ~20–40 min |
| 3 | Asks the local operator where the equipment physically is | ~5–15 min |
| 4 | Walks the plant, often taking a wrong route around blocked areas | ~10–20 min |
| 5 | Decides the action, often with incomplete context | — |
| | **Total time-to-act** | **~40–80 min** |

### After (with our product) `[HYPOTHESIS]`

| Step | With Point, Path, Why | Est. time |
|---|---|---|
| 1 | Opens the plant twin; the equipment needing attention is already glowing red | ~10 s |
| 2 | Taps it: name, ID, status, and a cited explanation of *why* it needs attention | ~30 s |
| 3 | Taps "Route": the walkable path from the entrance appears in 3D, with distance and time | ~10 s |
| 4 | Arrives prepared | walking time only |
| | **Total prep time** | **< 2 min** |

**Headline ROI claim (placeholder):** *"From ~1 hour of searching to under 2 minutes of preparation per job."* `[HYPOTHESIS]`. Replace it with partner numbers.

---

## 2. The One-Screen Product UI spec

```
┌──────────────────────────────────────────────────────────────────────┐
│ [INPUT] "Which equipment needs attention, and how do I get there?" [Ask]│
│  Samples: [⚠ What needs attention?] [🧭 Route to pump P-101] [❓ Why is │
│            the gearbox on watch?]                                       │
├───────────────────────────────────────────┬──────────────────────────┤
│                                           │ [OUTPUT] Action card       │
│   CENTRAL 3D VIEW                         │  ▸ Asset: Pump P-101       │
│   • point cloud / mesh of the plant       │  ▸ Status: ALERT           │
│   • equipment boxes colored by health     │  ▸ Why: vibration trend…   │
│     (green ok / amber watch / red alert)  │    [cite: WO-2231, p.4]    │
│   • highlighted target + 3D route line    │  ▸ Route: 48 m · ~1 min    │
│                                           │  ▸ Next step: check …      │
├───────────────────────────────────────────┴──────────────────────────┤
│ PROOF 1: Time-to-locate 4 s (vs ~15 min baseline*)                      │
│ PROOF 2: 37/42 assets auto-labeled & linked to docs (88%)               │
│ [Demo Mode: ON]                     *baseline = [GAP - ASK PARTNER]     │
└──────────────────────────────────────────────────────────────────────┘
```

- **1 input:** a natural-language question plus 3 pre-loaded sample buttons (these are also the 3 Demo Mode cached inputs).
- **1 central view:** a 3D scene with semantic overlays and the route.
- **1 actionable output:** an action card with cited reasoning.
- **2 proof metrics:** time-to-locate, and the share of assets auto-labeled and linked. Values above are illustrative only `[HYPOTHESIS]`.

---

## 3. MoSCoW requirements

### MUST: Gate 2 (Sat 09:00)

| ID | Requirement | Acceptance test | Owner | Est. h |
|---|---|---|---|---|
| M1 | **Data adapter, Branch A/B:** `DataSource` interface with `SyntheticSource` (procedural plant) and `PartnerSource` stub | `DATA_SOURCE=synthetic` loads a scene with ≥ 20 labeled assets; swapping to `partner` takes 1 file edit | CV | 4 |
| M2 | **Synthetic plant generator:** point cloud with ground-truth labels, assets.json, docs, work orders, alarms | `python -m tools.gen_synthetic` finishes in < 2 min and writes `/data/synthetic/*` | CV | 4 |
| M3 | **3D viewer:** render the point cloud or mesh with asset bounding boxes colored by health | Scene loads in < 5 s on a laptop and stays ≥ 30 fps when orbiting | FE | 5 |
| M4 | **Equipment detection v0:** clustering-based segmentation that outputs `Asset[]` | Produces asset boxes on the synthetic scene; IoU vs. ground truth is logged | CV | 5 |
| M5 | **Navigation v0:** floor detection → occupancy grid → A* route to a target asset | Route returned in < 1 s and never passes through occupied cells | CV | 4 |
| M6 | **Ask endpoint v0:** question → target asset + route + answer (LLM over linked docs) | 3 sample questions return valid `AskResponse` JSON | AI | 4 |
| M7 | **One-Screen UI wired end-to-end** | Typing a sample question highlights the asset, draws the route and fills the action card | FE | 4 |
| M8 | **Demo Mode toggle** with cached JSON for the 3 sample inputs | With the network off and Demo Mode on, all 3 samples work identically | AI | 2 |

### SHOULD: Gate 3 (Sat 16:00)

| ID | Requirement | Acceptance test | Owner | Est. h |
|---|---|---|---|---|
| S1 | **Semantic labeling v1 (differentiator):** classify detected clusters (rendered views → vision model, or a geometric classifier) | ≥ 80% correct class on the synthetic ground truth; on real data, judged by the partner `[GAP - ASK PARTNER]` | CV/AI | 6 |
| S2 | **Grounded explanations with citations** | Every answer cites ≥ 1 doc ID; with no supporting doc it says "insufficient data" | AI | 4 |
| S3 | **Proof metrics live:** time-to-locate timer, % assets labeled and linked | Both metrics update after each query | FE | 2 |
| S4 | **Person vs. robot routing** (clearance parameter) | Robot mode avoids passages narrower than the configured width | CV | 3 |
| S5 | **Health status from events** (real alarms in Branch A, synthetic in Branch B) | Changing an event file changes asset colors on reload | AI | 2 |

### COULD: Gate 4 (Sun 02:00)

| ID | Requirement | Acceptance test | Owner | Est. h |
|---|---|---|---|---|
| C1 | Export the scene graph and navmesh for robotics simulation (e.g. ROS occupancy map) | Exported map opens in a standard viewer | CV | 3 |
| C2 | Smooth camera fly-to on the target asset | Camera animates to the target in < 1.5 s | FE | 2 |
| C3 | Work-package PDF/markdown export (Wedge 2 bonus) | One click generates a work package file | AI | 2 |
| C4 | Voice input for hands-free use | Spoken sample question works | FE | 2 |

### WON'T (anti-scope)

- Auth / login screens, user management
- Settings pages
- Multi-page CRUD for assets or documents
- Live sensor streaming integration
- Mobile-native apps (the responsive web UI is enough)

---

## 4. Traceability matrix

| Req ID | README phrase | Judging criterion | 2-min video moment |
|---|---|---|---|
| M1, M2 | "Today's 3D captures … lack the meaning" | Production viability (real or synthetic data both work) | 0:00–0:15: "beautiful scan, zero meaning" hook |
| M3, M4, S1 | "where machines are, what they are" | Innovation / wow | 0:15–0:40: equipment lights up, labeled |
| M5, S4 | "how people or robots could move between them" | Innovation / viability | 0:55–1:10: route drawn for person, then robot |
| S5 | "which equipment needs attention" | Business impact | 0:40–0:55: red asset found instantly |
| M6, S2 | "explain the context behind a maintenance decision" | Business impact / trust | 1:10–1:30: cited explanation |
| S3 | "find the right equipment faster" | Measurable business impact | 1:30–1:45: proof metrics + ROI line |
| M7, M8 | "A strong demonstration" | Viability (live, no mockups) | Whole video is a live screen capture |
| C1 | "robotics simulation", "autonomous systems" | Innovation | 1:45–2:00: "and robots can use it too" |
