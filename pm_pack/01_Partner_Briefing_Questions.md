# 01 — Partner Briefing Questions (Valmet)

> ⚠️ **PROVISIONAL: BASED ON MISSING DATA.**
> This pack was generated from `README.md` alone, which is a short challenge description of about 170 words. We had **no datasets, API docs, NDA terms, evaluation criteria, team size or team roles**. Claims are tagged `[README]` (written in the README), `[HYPOTHESIS]` (our deduction) or `[GAP - ASK PARTNER]` (unknown). Re-validate everything after the Fri 19:30 briefing and update this pack with the answers (use the copy button in `01b_Partner_Briefing_Card.html`).

**Working wedge:** Wedge 1, the "Point, Path, Why" plant twin `[HYPOTHESIS]`. It is the recommended choice and has not been confirmed with the partner.

---

## ⏱ Top 5: "If we only get 3 minutes"

| # | Question | Why we ask → How the answer changes our code |
|---|---|---|
| T1 | **What exactly do we get at 19:30: a raw point cloud, a mesh, 360° images or splats? In which file format, how large, and covering how many plant areas?** | The README only says "3D captures" `[README]`. → This picks the viewer (three.js points vs. Potree vs. a mesh), the downsampling strategy, and whether we run Branch A (real data) or Branch B (synthetic plant). |
| T2 | **Is there equipment information we can link to the scan, such as an asset register with IDs, P&IDs, manuals, work orders or alarm/condition data?** | "AI-grounded equipment information" `[README]` has no schema. → This decides whether the assistant does RAG over real documents, and whether "needs attention" comes from real alarms or from synthetic events. |
| T3 | **Can scan data and documents go to cloud AI APIs, or must they stay local / use open-weight models? Can we show the data in a public video?** | → This chooses between the cloud LLM and the local model in `AGENTS.md`, and decides whether the demo video must use the synthetic plant. |
| T4 | **Who is the primary user on Monday morning: a field service expert on a tablet, a remote expert, or a robot/autonomous system in simulation?** | The README names both "service experts" and "autonomous systems" `[README]`. → This sets the UI (touch-first vs. desktop) and whether a robot-sim export (ROS/Isaac format) is a SHOULD or a COULD. |
| T5 | **Since the README leaves the format open, what single live action or metric on screen on Sunday morning separates 1st place from 2nd?** | → This reorders the MoSCoW list, so the winning moment becomes the 0:30 mark of our video. |

---

## Unpacking the README wording

| # | README phrase | Question | Why we ask → Code impact |
|---|---|---|---|
| 6 | "Today's 3D captures can be visually extraordinary—but they often lack the meaning" | Which capture tool and workflow does Valmet use today, and where exactly does it fall short in a real service visit? | → Shows whether we compete with an existing viewer or plug into it. It changes whether we build our own viewer or an overlay/export layer. |
| 7 | "where machines are, what they are" | Is there a fixed list of equipment classes you care about most (pumps, motors, gearboxes, valves, rolls…)? Is there any labeled ground truth? | → Gives a closed-vocabulary classifier (more accurate) vs. open-vocabulary detection, and lets us show a measured accuracy number instead of a claimed one. |
| 8 | "how people or robots could move between them" | Does navigation mean walkable routes for people, robot-traversable paths (clearance, slopes, stairs), or both? Do you have safety zones? | → Sets the path-planning constraints: occupancy-grid resolution, minimum clearance, and stair/ladder handling. |
| 9 | "which equipment needs attention" | Where does "needs attention" come from today: condition monitoring alarms, maintenance schedules, or the technician's judgment? | → This becomes the health-status source: a real alarm feed (Branch A) or synthetic events (Branch B). |
| 10 | "explain the context behind a maintenance decision" | What does a good explanation look like to a Valmet service expert? Which sources must it cite? | → Sets the citation format and the system prompt of the assistant, and is our anti-hallucination rule. |
| 11 | "fragmented technical data" | In how many systems does a technician look today to prepare one job, and roughly how long does it take? | → This gives our **baseline for the ROI metric** (time-to-locate / time-to-prepare). Without it, the ROI stays `[HYPOTHESIS]`. |

## Data & NDA reality check

| # | Question | Why we ask → Code impact |
|---|---|---|
| 12 | Will there be more data or API access on Saturday, or is 19:30 everything? | → Decides whether we freeze the data adapter Friday night or keep Branch A open. |
| 13 | Is there GPU compute provided, or a size limit for what we can process? | → Heavy 3D segmentation (Wedge 3) vs. lightweight clustering + vision-model labeling (Wedge 1). |
| 14 | Can we keep a cached, anonymized subset in a public GitHub repo for judging? | → Defines what goes into `/data/cache/` and what stays gitignored. |

## The Sunday 10:00 evaluator question

| # | Question | Why we ask → Code impact |
|---|---|---|
| 15 | *"Since the README leaves the exact format open, what single live action or metric on screen on Sunday morning separates 1st place from 2nd place?"* Also: who evaluates, Valmet engineers or a general jury? | → Technical jury: show pipeline depth and accuracy. General jury: show the 15-second "wow" and the ROI number. |

---

## 🎤 Three 2-sentence pitch scripts (read aloud and watch their reaction)

**Wedge 1: "Point, Path, Why" plant twin**
> "We turn your scan into a plant that knows itself: every machine is found, named and colored by health. You ask 'what needs attention and how do I get there?' and it highlights the asset, draws the walking route and explains why, with citations from your documents."

**Wedge 2: Maintenance work-package agent**
> "When an alarm fires, our agent builds the complete work package in seconds: where the equipment is, a picture of it, the route, the safety steps and the parts, all from your fragmented documents. The technician arrives prepared instead of searching."

**Wedge 3: Scan-to-semantic-twin pipeline**
> "We built a pipeline that turns a raw point cloud into a semantic digital twin: equipment instances, a scene graph and a navigation map that robots can use in simulation. Every detected asset is linked to its technical documentation, so the twin is both navigable and explainable."

**What to listen for:** which pitch makes them lean in, and which nouns they repeat back ("robots"? "technician"? "documents"?). Write it down in the HTML card.
