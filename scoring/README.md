# Scoring

How Valmet will judge the build, what that means for what we build first, and a self-score we update at every roadmap gate.

**Source of truth:** sections 06 (evaluation criteria) and 07 (submission format) of `Source-Data-Do-Not_change/Valmet_x_SinceAI_2026_Challenge_Brief_FINAL_updated (1).docx`, plus hints from the Excel builder pack. The wedge-D PRD (`pm_pack/02_Requirements_Management_PRD.md`) maps its requirements to the same five criteria. This folder adds what the PRD lacks: sub-criteria, measurable targets and a running self-score.

| File | What it is |
|---|---|
| `README.md` | The rubric, what matters most, and where our wedge gains or loses points |
| `scorecard.toml` | 18 sub-criteria with points, measurable targets and 0–5 anchors, plus the pass/fail checklist. The team fills in values and scores |
| `score.py` | Prints the weighted total out of 100, the biggest point gaps and the open checklist items (standard library only) |

```bash
python3 scoring/score.py
```

---

## 1. The official rubric

| ID | Criterion (brief §06) | Weight | What the judge checks | Our proof on screen |
|---|---|---|---|---|
| J1 | Semantic asset extraction density & 3D framing | **30** | How many objects in `Industrial Boiler Room.ply` get a 3D frame and Excel metadata. "The more, the better." | Live counter of framed and mapped assets; red/grey snapshot trail |
| J2 | Realistic obstacle-aware navigation & proximity display | **25** | The avatar or robot computes and walks a logical floor path to the faulty device without passing through walls, boilers or piping. Nearby assets light up as it passes | Occupancy grid under the path, a clearance number, frames lighting up along the walk |
| J3 | AI diagnostics, grounding & explainability | **20** | Device status is explained along the path; at the faulty device the advice is grounded in the Excel pack | Diagnosis card with evidence IDs, confidence and safe next steps |
| J4 | Backend architecture & technical implementation | **15** | The pipeline is structured, automated and modular | One command from raw files to scene; stage diagram |
| J5 | Demo clarity & innovation | **10** | The demo is easy to follow and runs reliably | A short, clean video; the approve-to-build loop; Quest 3 as a bonus |

The brief says it directly: a light visualization with strong spatial processing beats a polished app with weak processing. UI polish can earn at most part of J5.

## 2. What matters most

1. **55 of 100 points come from spatial processing of the PLY (J1 + J2).** Most build hours go there. Only about a third of the 1.5 M gaussians in the scan are usable; the rest are far-away floaters or collapsed at the origin. Filtering them is step zero, because every frame placed on a floater lowers J1.2.
2. **Asset count is the headline number.** "The more, the better" appears three times in the brief. Show the count on screen, on slide 1 and in the video. The wedge-D PRD's M3 target (≥ 40 proposals, 15 of the top 20 real) earns about 12 of the 20 points in J1.1 + J1.2. That is a floor to pass, not a target that wins.
3. **The Excel pack has only 30 assets, and we want more frames than that.** The brief allows random or procedural mapping. Put the 30 real `Asset_Master` rows on clusters of a plausible type (the faulty target ASSET-017 / P-005 is a `PROCESS_PUMP`, criticality A). Give the remaining frames procedural "normal" records. Say it honestly on screen: "30 from the pack + N procedural = 100% mapped".
4. **The pack asks for exactly the remap we are doing.** `Scene_Anchors` coordinates are placeholders (`mapping_status = placeholder_until_valmet_scene_received`, `mapping_confidence = 0.65`) with the instruction to remap them to the real scene path and bounds. If we write our frames back into that schema (real bbox, new status, new confidence), J1.4 becomes a story the authors will recognize.
5. **Collision-free must be provable, not just visible.** Log the path's minimum clearance against the occupancy grid and show the grid under the path for a few seconds. One frame of the avatar inside the boiler costs more than any polish can win back.
6. **Grounding means evidence IDs and confidence.** The pack's own `Builder_Questions` mark these as P0: Q-03 (every diagnosis with exact evidence IDs and confidence), Q-06 (lower confidence when sensor or mapping quality is poor) and Q-02 (detect degradation from multivariate telemetry). The pack's `API_Contract` says the copilot returns a "safe next check", and work orders are drafts only, never control actions.
7. **J4 points are cheap now and expensive later.** Build the pipeline from the first commit as stages with files between them and one entry point. Serving a few routes from the pack's `API_Contract` (`/api/assets`, `/api/scene/anchors`, `/api/copilot/query`) shows production thinking at little cost.
8. **The video is what most judges will see.** The cap is 5 minutes. Spend the time in proportion to the weights (§5).
9. **Quest 3 is worth at most about 2 points** (half of J5.2). Start it only after the pass/fail checklist is complete.

**Build order by points per hour:**

| # | Work | Rubric items | Points |
|---|---|---|---|
| 1 | Clean the scan, cluster, frame, plus a thin approve loop | J1.1, J1.2 | 20 |
| 2 | Occupancy grid, path, clearance check | J2.1–J2.3 | 17 |
| 3 | Excel mapping, including the target (about 1 h) | J1.4 | 5 |
| 4 | Auto-walk and proximity highlight | J2.4, J2.5 | 8 |
| 5 | Labels, snapshot-trail polish | J1.3, J5.2 | 5–9 |
| 6 | Quest 3 | part of J5.2 | ≤ 2 |

**In parallel**, the AI track builds J3 (20 points) from the Excel pack alone. It needs no geometry until the avatar arrives, so it can start immediately.

## 3. Where wedge D (Approve-to-Build) gains or loses points

| Non-negotiable | Helps | Costs | Keep it, but… |
|---|---|---|---|
| 1. One-by-one approval | J1.2 precision (a person rejects floaters and merged boxes); the J3 trust story | J1.1 density (every object needs a decision) and J4.1 automation | The pipeline proposes all candidates automatically. Approval is one key press (A / R) with the next candidate already framed. Approve the full set before the demo and show the live loop on 3–5 objects. Add `--auto-approve` so the pipeline also runs unattended |
| 2. Web interface for approval | – | Time taken from J1/J2 if it grows | One screen: candidate view, approve/reject, counter |
| 3. Offline model work | J5.1 reliability (the demo works with Wi-Fi off); repeatable answers | J3 answer quality if the local model is weak | Retrieval and templates carry the facts and IDs; the model only writes the sentences |
| 4. Red/grey snapshot after each addition | J1 evidence, video material, J5.2 innovation | Render time per approval | Render in the background; play the snapshots as a flipbook in the video |
| 5. Walkable three.js + Quest 3 | J2.4/J2.5 rendering, J5.2 | **Risk:** a free-walk mode scores nothing in J2. The brief requires the avatar to walk the computed path **by itself** | Build the auto-walk first. Make the free walk use the same occupancy grid so users cannot walk through walls either |

## 4. Pass/fail: missing any of these puts everything at risk

Submission package (brief §07): working demo, repo with README and setup, 5–8 slides covering four named topics, video of at most 5 minutes, technical note. Also the six "at minimum, the demo must" points. They are `SUB-1…5` and `DEM-1…6` in `scorecard.toml`; `score.py` lists the ones still open.

## 5. Video and slides, by weight

The wedge-D PRD plans a cut of at most 3:30 (the cap is 5:00). Check the storyboard against the weights. Screen time per criterion should roughly follow them:

| Criterion | Weight | Share of a 3:30 cut | Must be on screen |
|---|---|---|---|
| J1 | 30 | ≈ 60 s | The raw scan, then every frame plus the counter; approve loop with red/grey snapshots; Excel rows landing on frames; ASSET-017 turning red |
| J2 | 25 | ≈ 55 s | Grid under the path, the clearance number, the avatar walking by itself, nearby frames lighting up with metadata |
| J3 | 20 | ≈ 40 s | Diagnosis with evidence IDs, confidence, safe next steps, work-order draft |
| J4 | 15 | ≈ 30 s | One command running, stage diagram, runtimes |
| J5 | 10 | ≈ 20 s | Quest 3 clip if it exists; the closing numbers |

Slides (the brief requires 5–8 and names four topics, marked ★):
1. The result in numbers
2. ★ 3D semantic extraction pipeline
3. ★ Obstacle-free pathfinding
4. ★ Excel metadata mapping
5. ★ AI approach
6. Architecture and technical note summary
7. Self-score and metrics (from `score.py`)
8. Next steps: real feeds (Builder Q-07), Quest 3

## 6. Using the scorecard

- After each roadmap gate, update `value` on the metric items (or have the pipeline write `metrics.json` and pass `--metrics`), set `score` 0–5 on the judgment items using their anchors, and set `done = true` on finished checklist items.
- Metric keys the pipeline should write to `metrics.json`: `framed_assets`, `labeled_pct`, `mapped_pct`, `min_clearance_ratio`, `proximity_assets_surfaced`, `citation_valid_pct`, `pipeline_manual_steps`. A person fills `spot_check_precision` by looking at 20 random frames.
- The thresholds are our guesses `[HYPOTHESIS]`, for example 100 frames for full marks on density. Recalibrate them after the first clustering run, then freeze them so scores stay comparable from gate to gate.

```bash
python3 scoring/score.py --metrics out/metrics.json --top 8
```
