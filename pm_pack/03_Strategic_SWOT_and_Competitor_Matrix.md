# 03 — Strategic SWOT & Competitor Matrix

> ⚠️ **PROVISIONAL: BASED ON MISSING DATA.**
> Generated from `README.md` only. There were no datasets, evaluation criteria, team composition or knowledge of the competing teams. Predictions about other teams and judges are `[HYPOTHESIS]`. Revisit after the briefing and the Saturday-morning partner check.

---

## 1. SWOT

| | **Helpful** | **Harmful** |
|---|---|---|
| **Internal** | **Strengths** <br>• A clear, single-screen story that covers all four README "understands" points `[README]` <br>• Branch A/B data adapter: we can demo even if the partner gives us nothing usable <br>• Deterministic Demo Mode means a reliable live demo <br>• Grounded, cited answers instead of a free-form chatbot | **Weaknesses** <br>• Team size and skills unknown `[GAP]` <br>• 3D segmentation on real industrial scans is hard; accuracy on real data is unproven <br>• The ROI baseline is a guess until the partner gives numbers <br>• Only ~38 build hours |
| **External** | **Opportunities** <br>• **The narrow README is our biggest advantage.** `[HYPOTHESIS]` Most teams faced with a vague prompt build a generic chatbot wrapper. We build a specific operational tool that maps point by point to the README wording. <br>• The partner Q&A on Saturday lets us course-correct while others are locked in <br>• The robotics-simulation angle (`[README]`) is a stretch hook few teams will touch | **Threats** <br>• Partner data arrives late, huge or under NDA `[GAP]` <br>• A team with deep 3D/robotics expertise builds a stronger pipeline (Wedge 3 style) <br>• The jury may weigh technical depth over UX `[GAP - ASK PARTNER]` Q15 <br>• Venue Wi-Fi or API outages during the live demo |

### Why the narrow README helps us `[HYPOTHESIS]`

A short README with many buzzwords ("digital twins, robotics simulation, assistant") tempts teams to pick **one** buzzword and build a demo of it. Judges from Valmet wrote the **whole chain** (locate → identify → navigate → prioritize → explain). The team that visibly closes the chain on one screen, and quotes the README back to them, signals that they understood the problem rather than the technology.

---

## 2. Competitor matrix: our wedge vs. three "lazy README interpretations"

| Dimension | **Us: Point, Path, Why** | Lazy #1: "Maintenance chatbot" (RAG over PDFs) | Lazy #2: "Pretty 3D viewer" (scan + hotspots) | Lazy #3: "Segmentation research demo" (notebook) |
|---|---|---|---|---|
| Uses 3D space | ✅ core | ❌ none | ✅ visual only | ✅ core |
| Knows *what* equipment is | ✅ auto-labeled | ⚠️ text only | ❌ manual hotspots | ✅ |
| Navigation for people/robots | ✅ route in 3D | ❌ | ❌ | ❌ usually |
| "Needs attention" prioritization | ✅ health colors | ⚠️ if asked | ❌ | ❌ |
| Explains *why* with citations | ✅ | ✅ | ❌ | ❌ |
| One-screen 15-s clarity | ✅ | ⚠️ looks like any chatbot | ✅ but shallow | ❌ plots and metrics |
| Works with zero partner data | ✅ synthetic plant | ✅ | ❌ needs scan | ❌ needs scan |
| Measurable ROI shown | ✅ time-to-locate | ⚠️ | ❌ | ⚠️ accuracy only |
| Production viability | ✅ end-to-end, live | ✅ but generic | ⚠️ mockup-like | ❌ not a product |

**How we beat a strong Wedge-3-style team:** they will have the deeper pipeline. We win on **closing the loop to a maintenance action** and on business impact. If Q15 says the jury is deeply technical, move S1 (semantic labeling) earlier and show accuracy numbers.

---

## 3. Strategic verdict

**Unfair advantage (1 sentence):**
> We are the only team whose demo closes the whole loop the README asks for (find, identify, route, prioritize and explain) on one screen, with or without partner data.

**30-second elevator pitch:**
> "Valmet's plant scans look perfect but don't know anything: not where the pump is, not what it is, not how to reach it. We turn a scan into a plant twin that does. Every machine is detected, labeled and colored by health. Ask 'what needs attention and how do I get there?' and it highlights the equipment, draws the walking or robot route, and explains the maintenance reason with citations from your own documents. A service expert goes from an hour of searching across systems to under two minutes of preparation, and the same map is ready for autonomous robots."

*(The "hour → two minutes" figure is `[HYPOTHESIS]`. Replace it with the partner's baseline.)*
