`// VALMET × SINCE AI 2026 · PM PACK · 01`

# 01 — Partner Briefing Questions

The interrogation script for the Valmet reps (Mika Karaila, Alp Aydin `[SOURCE DATA — brief §08]`) at the stand, in Discord and in the mentoring windows. Every question maps to a gap `G1–G8` found in the source data and says how the answer changes our code.

`v1.0.0 · GENERATED 2026-11-06 20:50 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data. `[HYPOTHESIS]` = our deduction or design choice. Phone version with text inputs and the copy-to-Claude button: `01b_Partner_Briefing_Card.html`.

> [!TIP]
> **Lead with evidence.** Open every conversation with one measured fact ("we loaded your splat: 1.5 M gaussians, a third of them inside the room, y-up, about 8.6 by 4.4 units"). It proves we did the homework and turns the rep from a presenter into a collaborator.

---

## ⏱ Top 5 — the "3-minute stand" shortlist

| # | Gap | Ask this, verbatim | Why → what changes in our code |
|---|---|---|---|
| **T1** | `G1` `G2` | **"Is `Industrial Boiler Room.ply` in metres and y-up? We measure about 2.0–2.6 units floor-to-ceiling. And two thirds of the gaussians sit outside the room or at the origin — is that expected, and do you have a cleaner export or the camera poses?"** | Scale sets the agent clearance (`0.30 u`), grid cell (`0.05 u`), eye height and every number we show. Camera poses would unlock multi-view labelling (`S1`) instead of geometry-only guesses. A cleaner export shortens `M1`/`M3`. |
| **T2** | `G4` | **"For the 30 % density score, what counts as one asset — a pipe segment, a valve, structural steel? And does a human-approved extraction score fully, or must the extraction be fully automatic?"** | Decides whether our headline is `approved: 87` or `automatic: 137 / approved: 87`, whether over-segmentation of pipes is rewarded or punished, and whether `S1` (VLM labels) is worth four hours. |
| **T3** | `G5` `G3` | **"May we make `P-005` (fouling, health 44) the pre-determined faulty device and start the avatar at the room entrance? Also: the pack references `telemetry_full_14d_30min.csv` and 38 `DOC-*.md` files that aren't in the package — do they exist?"** | Fixes the demo script and `route.json`. The 14-day CSV would let the copilot show a real trend; without the `.md` cards we generate asset cards from the rows (`M6`). |
| **T4** | `G6` | **"Can scan views go to a cloud vision/LLM API, and may the scan and the data appear in a public GitHub repo and in our demo video?"** | Cloud = `S1` and the live copilot; no cloud = local model behind the same `LLMClient` and a private repo until Sunday. Public video = we can show the real room; otherwise we blur or render boxes only. |
| **T5** | `G7` | **"On Sunday, is it a live run on our laptop — can we hand a judge the Quest 3 — or video-first? And what single thing on screen separates 1st from 2nd place for you?"** | Reorders the MoSCoW list, sets whether `S3` (VR) is a wow moment or a liability, and becomes the 0:30 mark of the video. |

---

## Unpacking ambiguities in the source data

| # | Gap | Source phrase `[SOURCE DATA]` | Question | Why → code impact |
|---|---|---|---|---|
| Q6 | `G4` | "the more, the better" (brief §02, §06) | Is there a point where more boxes stop helping — do you prefer 60 clean objects over 200 fragments? Is a class label required, or is a framed, mapped object enough? | Sets the stopping rule for the Saturday approval run and the DBSCAN split threshold in `M3`. |
| Q7 | `G4` | "3D-frame" / "3D bounding boxes/frames" (§02 item 1) | Is an oriented box enough, or do you want a tight mesh per object? | Promotes `S2` (per-object meshes) to MUST or drops it. |
| Q8 | `G5` | "logical, real-world walkable route … avoid walls, boilers, piping" (§02 item 3) | Single floor only? Human or robot clearance? Is a route that hugs a pipe at 0.25 u acceptable? | Fixes grid dilation in `M2`/`M7`; stairs/platforms would be a scope cut (`WON'T`). |
| Q9 | `G5` | "all extracted assets near the robot are dynamically highlighted" (§02 item 4) | What radius counts as "near"? Line-of-sight or plain distance? | Sets the proximity ring (`1.5 u` today) in `M8`. |
| Q10 | `G5` | "a pre-determined faulty device" (§02 item 3) | One device, or should the demo switch between several? Who determines it — you on the day, or us? | Our three sample buttons (`P-005`, `M-006`, `P-002`) cover both answers; tells us whether to cache one or three diagnoses (`M11`). |
| Q11 | `G7` | "lightweight visualization … strongly preferred over a polished mobile app" (§06) | Does a three.js web app with a VR mode still count as lightweight, or would you rather see a Python viewer? | Confirms the whole Screen B; worst case we add a Rerun export of the same artifacts. |
| Q12 | `G4` | "random or procedural mapping is completely acceptable" (§02 item 2) | Is a human-approved, per-object mapping scored higher than random — and should we show the mapping confidence on screen? | Decides whether `mapping_confidence` is a visible proof metric. |
| Q13 | `G2` | `Scene_Anchors.mapping_status = placeholder_until_valmet_scene_received`; `START_HERE`: "Real Valmet scene — Not received yet" | The pack says the real scene wasn't received, but the brief ships the boiler room — is this *the* Valmet scene? Where was it captured and with what tool (`comment Generated by EGS` in the header)? | Tells us whether to present it as a Valmet site or a generic room, and whether a better export is realistic before Sunday. |
| Q14 | `G4` | "pipeline well-structured, automated, and modular" (§06 c4) | Is a human approval step compatible with "automated" in your scoring, if every automatic proposal is also logged? | If no: we headline the automatic count and demote the curator to QA in the pitch (code unchanged). |
| Q15 | `G3` | "explain device status along the path" (§06 c3) | Every asset in range, or only the ones with a non-normal state? | Scope of `S6`; affects copilot cache size. |

---

## Data & NDA reality check

| # | Gap | Question | Why → code impact |
|---|---|---|---|
| Q16 | `G3` | What exactly is the complete starter package? We hold `.ply`, three `.mp4`, the `.xlsx`, the brief and a `.ply.sha256` — anything else coming (poses, mesh, COLMAP, more scans)? | Avoids rebuilding on a stale file; poses change `M3`/`S1`. |
| Q17 | `G6` | Any NDA on the scan or the pack? May screenshots be shown to other teams and to peer voters? | Sets the public/private repo switch and what the video may contain. |
| Q18 | `G6` | Are there restrictions on cloud AI providers (region, retention) for the hackathon? | Picks Anthropic API vs local model in `api/llm_client.py`. |
| Q19 | `G8` | When exactly are the mentoring windows and who answers on Discord at night? | Puts Gate 2's partner check on the clock. |
| Q20 | `G7` | Do Since AI's own peer votes or stage finals affect the Valmet track ranking? | Decides how much polish goes into the 2-minute stage story versus the judge demo. |

---

## The Sunday evaluator question

Ask it plainly and write the answer down word for word: **"On Sunday morning, what single live metric or action on screen separates first place from second place for you?"**

Offer three candidates and watch which one makes them nod `[HYPOTHESIS]`:

1. **The counter with receipts** — `87 assets approved · 30 bound` next to a timelapse of snapshots that proves every object was looked at.
2. **The walk that never clips** — the avatar and the first-person walk both stop at the boiler because they share one occupancy grid.
3. **The diagnosis with evidence IDs** — a card that cites `EVT-00342`, `WO-00117`, `DOC-PROCESS_PUMP-CORE` and a 3-day telemetry window, with a confidence number and a safe next check.

Whatever they pick becomes the 0:30 mark of the video and the first thing on Screen B.

---

## Three 2-sentence pitch scripts (read aloud, test live)

**Pitch D — Approve-to-Build Twin (locked)**
> "We turn your boiler-room splat into a twin the way a service engineer would: the pipeline proposes objects one by one, a human approves each into the scene, and the twin photographs itself after every approval so you can audit how it was built. Then you walk it — on a laptop or in a Quest 3 — follow the avatar to the faulty pump along a path that never clips a wall, and get a diagnosis that cites the exact telemetry, events and documents from your pack."

**Pitch B — Walk to the Fault (fallback if the curator loop fails)**
> "A service avatar plans a collision-free route through your scanned boiler room to the pump that's fouling, highlighting every asset it passes with its live status from your data pack. When it arrives, the copilot explains the fault with evidence IDs, a confidence score and the next safe check — nothing is ever claimed without a citation."

**Pitch A — Every Object, Its Own Asset (if the partner wants fully automatic extraction)**
> "We extract and frame as many objects as the scan allows — automatically — and show the count climbing live, every box bound to your equipment data. The same scene then drives an avatar that walks to the faulty device and a copilot that explains why it needs attention."

---

## The ten questions on the phone card (`01b`)

The card carries these in this order, with a text input under each and a checkbox for "asked":

| # | Question (short form) | Gap |
|---|---|---|
| 1 | Units, up-axis, floor-to-ceiling height of the PLY | `G1` |
| 2 | Is 67 % junk expected? Cleaner export or camera poses available? | `G2` |
| 3 | What counts as one asset; does human-approved extraction score fully? | `G4` |
| 4 | OK to use `P-005` as the faulty target and the entrance as start pose? | `G5` |
| 5 | Do `telemetry_full_14d_30min.csv` and the 38 `DOC-*.md` files exist? | `G3` |
| 6 | Cloud VLM/LLM allowed? Public repo and video allowed? | `G6` |
| 7 | Sunday: live on our laptop, Quest hand-off, slot length, or video-first? | `G7` |
| 8 | The single metric that separates 1st from 2nd | `G7` |
| 9 | Mentoring windows and who answers on Discord at night | `G8` |
| 10 | Navigation semantics: human vs robot clearance, single floor, "near" radius | `G5` |

**After the briefing:** tap **Copy Partner Answers as Claude Update Prompt**, paste it into this session, and the pack gets re-tagged (`[GAP - ASK PARTNER]` → `[SOURCE DATA — partner, Fri briefing]`) and re-estimated.
