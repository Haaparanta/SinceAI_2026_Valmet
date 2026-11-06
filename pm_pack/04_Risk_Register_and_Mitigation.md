# 04 — Risk Register & Mitigation

> [!WARNING]
> **PROVISIONAL: BASED ON MISSING DATA.**
> Generated from `README.md` only. Likelihood and impact scores are estimates made **before** we know the data format, volume, NDA terms, evaluation criteria or team skills. Re-score after the Fri 19:30 briefing. Owners are role slots (**PM / CV / AI / FE**).

**Scale:** L = likelihood (1–5), I = impact (1–5), Score = L × I. Review at every gate.

| ID | Risk | L | I | Score | Trigger | Owner | Hard fallback |
|---|---|---|---|---|---|---|---|
| R1 | **Zero or dirty partner data at 19:30** (no scan, a broken file, or only images) | 3 | 5 | **15** | No usable 3D file in our hands by 20:30 | CV | Run `python -m tools.gen_synthetic` (≤ 15 min): a procedural plant hall with labeled pumps, motors, tanks, pipes and walkways, plus synthetic docs, work orders and alarms. Switch `DATA_SOURCE=synthetic`. Tell the partner on Saturday that we are "ready to swap in your data". |
| R2 | **Partner data huge** (multi-GB point cloud) and slow to load or process | 3 | 4 | 12 | Load or processing of one area takes > 2 min | CV | Crop to one plant area and voxel-downsample (e.g. 2–5 cm). Precompute assets and the grid offline into `/data/cache/`. The viewer only loads the downsampled file. |
| R3 | **NDA forbids cloud AI APIs** or public video of the data | 2 | 4 | 8 | Partner says "no cloud" / "no public footage" (Q3) | AI | Local open-weight LLM and embeddings behind the same `LLMClient` interface. The video and public repo use the synthetic plant only. |
| R4 | **README misinterpretation:** we build the wrong thing | 3 | 5 | **15** | Partner reaction at the Sat 09:00 check is lukewarm, or they emphasize a different user (robots vs. technicians) | PM | **Mandatory live prototype demo to the partner at Sat 09:00 Q&A**, with the ugly end-to-end version. Pre-agreed pivot: shift emphasis to Wedge 2 (work package) or Wedge 3 (robot export) by reusing the same backend contracts. |
| R5 | **Semantic labeling inaccurate on real industrial scans** | 4 | 3 | 12 | < 60% correct labels on the partner sample | CV | Hybrid approach: auto-label plus a quick manual correction pass on the 5–10 demo assets. Show the honest accuracy number and frame it as "human-in-the-loop". Keep the synthetic scene for the accuracy metric. |
| R6 | **Live demo / API failure** (Wi-Fi, rate limits, LLM latency) | 3 | 5 | **15** | Any request > 5 s or an error during rehearsal | AI | **Deterministic cached Demo Mode toggle:** pre-computed `AskResponse` JSON for the 3 sample inputs stored in `/data/cache/`. The UI shows identical results offline. Rehearse with the network off. |
| R7 | **LLM hallucinates** maintenance advice | 3 | 4 | 12 | Answer without a citation, or citing a non-existent doc | AI | Hard rule: answers must cite doc IDs present in the retrieved set. Otherwise the response is "Insufficient documentation". Validate citations server-side. |
| R8 | **Point cloud viewer performance** on the demo laptop | 2 | 4 | 8 | < 30 fps or a browser crash | FE | Cap rendered points (e.g. ≤ 2M), use LOD, or render a precomputed mesh. Rehearse on the actual demo machine. |
| R9 | **Team capacity unknown / burnout** | 3 | 3 | 9 | Gate missed by > 1 h | PM | Sleep shifts in the roadmap. Cut COULD items first, then S4/S5. Never cut M7/M8. |
| R10 | **Submission logistics** (video render, upload, repo access) | 2 | 5 | 10 | Video not rendered by Sun 08:00 | PM | Record the screen capture at Gate 4. The deck is exported to PDF early. FINAL submission by 09:15, leaving 45 min of buffer. |

---

## Branch B: 15-minute synthetic data fallback (spec)

`tools/gen_synthetic.py` `[HYPOTHESIS: our design, not partner-provided]` produces:

| Output | Content |
|---|---|
| `data/synthetic/scene.ply` | A ~40 × 25 m hall: floor, walls, 3–4 rows of equipment (cylinders = tanks/rolls, boxes = motors/pumps, pipe runs), walkways, plus noise (σ ≈ 1 cm) |
| `data/synthetic/assets.json` | Ground-truth `Asset[]` (ID, class, bbox, health) for ≥ 20 assets |
| `data/synthetic/docs/*.md` | Short manuals and maintenance notes per equipment class |
| `data/synthetic/work_orders.csv` | Past work orders per asset (date, symptom, action) |
| `data/synthetic/events.json` | Alarms / condition alerts that drive "needs attention" |

All synthetic text is clearly labeled as synthetic in the UI (a "Synthetic data" badge).

---

## Sunday 10:00 pre-mortem: top 3 ways teams misread this README and lose `[HYPOTHESIS]`

1. **"It's a chatbot challenge."** They build RAG over PDFs and ignore physical space. The README's central line is *"make AI understand not just words and numbers, but physical space"* `[README]`. → **We must show 3D space understanding in the first 20 seconds.**
2. **"It's a 3D visualization challenge."** They build a beautiful viewer with manual hotspots. The README explicitly says visual quality is *not* the problem ("visually extraordinary—but … lack the meaning") `[README]`. → **We must show automatic semantics, not manual annotation.**
3. **"It's a research challenge."** They deliver segmentation metrics in a notebook with no user and no action. The README ends on *"confident, context-aware action"* for *"service experts and autonomous systems"* `[README]`. → **We must end the demo on an action card that a real person or robot uses.**

**Our own most likely failure mode:** spreading effort across all four README points and finishing none. The gates in `05_Execution_Roadmap_and_Milestones.md` force an *ugly but complete* loop by Sat 09:00.
