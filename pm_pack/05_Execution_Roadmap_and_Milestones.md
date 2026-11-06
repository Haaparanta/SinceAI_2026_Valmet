# 05 — Execution Roadmap & Milestones

> ⚠️ **PROVISIONAL: BASED ON MISSING DATA.**
> Generated from `README.md` only. Sprint content assumes Wedge 1 and an unknown team of roughly 4 people (**PM / CV / AI / FE** role slots) `[HYPOTHESIS]`. Task durations will change once we know the partner's data format and volume. Re-plan at Gate 1.

**Timeline (EET):** build starts **Fri 19:30**. Partner Q&A on **Sat morning/afternoon**. Hard deadline **Sun 10:00**. Internal FINAL target: **Sun 09:15**.

Each gate is **binary**: either every check passes, or we execute the listed kill/pivot action. No "almost".

---

## Sprint plan

| Sprint | Window | PM | CV (3D) | AI (backend/LLM) | FE (UI) |
|---|---|---|---|---|---|
| **S0 — Briefing & bootstrap** | Fri 19:30–22:30 | Run briefing with `01b` card, paste answers into Claude, choose Branch A/B | Inspect partner data **or** run synthetic generator; load + downsample | Repo scaffold, FastAPI, Pydantic contracts, `DataSource` interface | Vite + React + three.js skeleton rendering a point cloud |
| 🚦 **Gate 1** | **Fri 22:30** | | | | |
| **S1 — Ugly loop** | Fri 22:30–02:30 | Write demo script v0, define 3 sample questions | Clustering → `Asset[]`; floor → occupancy grid → A* | `/ask` v0: intent → target asset → route + LLM answer | Wire input → highlight + route line + action card |
| 💤 Sleep shift A | 02:30–06:30 | PM + FE sleep | CV + AI finish loop, then sleep 05:00–09:00 | | |
| **S2 — Partner-ready** | Sat 06:30–09:00 | Prepare partner demo + feedback questions | Fix route bugs | Demo Mode cache for 3 samples | Health colors, layout polish (minimal) |
| 🚦 **Gate 2** | **Sat 09:00** (live demo to partner) | | | | |
| **S3 — Differentiator** | Sat 09:00–13:00 | Integrate partner feedback → update PRD priorities | S1 semantic labeling v1 | S2 grounded citations + validator | S3 proof metrics |
| **S4 — Harden** | Sat 13:00–16:00 | Draft deck + video storyboard | S4 person/robot routing | S5 health from events; re-cache Demo Mode | Fly-to camera, sample buttons |
| 🚦 **Gate 3** | **Sat 16:00** | | | | |
| **S5 — Polish** | Sat 16:00–20:00 | Pitch rehearsal #1, ROI numbers | Accuracy eval on ground truth | Edge cases, "insufficient data" path | UI polish, "Synthetic data" badge |
| **S6 — Stretch** | Sat 20:00–Sun 00:00 | Deck v1 | C1 robot-sim export (if green) | C3 work-package export | C2/C4 (if green) |
| **S7 — Freeze** | Sun 00:00–02:00 | Setup README check | Final cache regen | Final cache regen | Bug fixes only |
| 🚦 **Gate 4** | **Sun 02:00** (feature freeze) | | | | |
| 💤 Sleep shift B | 02:00–06:00 | All sleep except one on-call | | | |
| **S8 — Ship** | Sun 06:00–08:00 | Record <2:00 video (live screen capture), export PDF deck | Clean repo | Verify Demo Mode offline | Rehearse on demo laptop |
| 🚦 **Gate 5** | **Sun 08:00** | | | | |
| **Submit** | Sun 08:00–09:15 | Upload video, deck, repo; mark **FINAL by 09:15** | | | |
| Buffer | 09:15–10:00 | Do not touch anything | | | |

---

## Gates: binary pass / kill / pivot

### 🚦 Gate 1 — Fri 22:30
**Pass if all are true:**
- [ ] Briefing answers pasted into Claude and `pm_pack/` updated (gaps resolved or explicitly still open)
- [ ] Real **or** synthetic seed data loads via `DataSource` (`DATA_SOURCE=partner|synthetic`)
- [ ] One-Screen UI skeleton runs locally and shows the point cloud

**If it fails:** force `DATA_SOURCE=synthetic` immediately and park partner-data parsing as a side task for one person.

### 🚦 Gate 2 — Sat 09:00
**Pass if all are true:**
- [ ] Working, ugly end-to-end pipeline: question → highlighted asset → route → answer
- [ ] Shown **live to the partner** at the Saturday Q&A, with feedback written down
- [ ] Demo Mode returns cached results for the 3 samples

**If it fails:** cut S4 and S6 and put everyone on closing the loop. **Pivot** if partner feedback says we're solving the wrong problem: switch emphasis to Wedge 2 or 3 and reuse the contracts (see R4).

### 🚦 Gate 3 — Sat 16:00
**Pass if all are true:**
- [ ] Partner feedback locked into PRD priorities
- [ ] Primary AI differentiator works (semantic labeling v1 **and** cited explanations)
- [ ] Both proof metrics show live values

**If it fails:** drop all COULD items. Use a manual-correction fallback for labels (R5).

### 🚦 Gate 4 — Sun 02:00
**Pass if all are true:**
- [ ] **Feature freeze:** no new features after this point
- [ ] Deterministic Demo Mode cache populated and tested with the network off
- [ ] Repo `README.md` has setup instructions that take < 5 min (fresh clone → running demo)

**If it fails:** strip unfinished features behind flags. Demo Mode is non-negotiable.

### 🚦 Gate 5 — Sun 08:00
**Pass if all are true:**
- [ ] < 2:00 video rendered (follow the timestamps in the PRD traceability matrix)
- [ ] PDF deck exported
- [ ] Submission uploaded and marked **FINAL by 09:15**

**If it fails:** submit what exists by 09:15 anyway. A complete but rough submission beats a missing one.
