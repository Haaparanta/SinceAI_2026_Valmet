`// VALMET × SINCE AI 2026 · RESEARCH · 05`

# 05: Offline AI copilot: grounded diagnosis at P-005 and VLM labels

Build the diagnosis as **deterministic evidence first, LLM wording second**. A Python batch step computes the numbers and picks the evidence IDs. A small local model (Qwen3.5 9B via Ollama, with schema-constrained JSON) only writes the explanation. A server-side validator rejects any answer that cites something it was not given. Every answer is cached to JSON. The demo replays the cache, so it works with Wi-Fi off. Live local inference is a bonus, not a dependency.

`2026-11-06 · INPUTS: Builder Pack xlsx v4.0 (read-only), web research · SERVES: c3 (20 %), c1 labels (30 %), c4 (15 %)`

---

## 1. Recommendation

### Runtime
- **Ollama** on the Mac, as the single local model server. It has a REST API, a Python client, JSON-schema `format`, and image input on the same endpoint. One tool covers both the LLM and the VLM.
- Pin the models with `ollama pull` **before** the event Wi-Fi gets busy. Copy `~/.ollama/models` to a USB stick as a backup.
- Use the default GGUF/Metal path. Ollama 0.19's MLX backend is a preview that needs a Mac with more than 32 GB of memory and was launched for one model (Qwen3.5-35B-A3B). Do not depend on it.
- Fallbacks: `llama-server` (llama.cpp) with `response_format` JSON schema, or `mlx-lm` / `mlx-vlm` in Python if Ollama misbehaves.

### Models
| Job | First choice | Fallback | Why |
|---|---|---|---|
| Diagnosis text + route one-liners | `qwen3.5:9b` (6.6–7.6 GB) | `qwen3.5:4b` (3.3–4.0 GB) or `gemma4:12b` | Recent (Mar 2026), text + image, tools, 256K ctx; fits a 16 GB Mac |
| Crop labels (VLM) | `qwen3.5:4b` or `:9b` with images | Moondream 3 Preview (MLX), Florence-2 | Same server and same schema code as the copilot |
| Cheap baseline / re-ranker | SigLIP 2 zero-shot (`transformers`) | open_clip ViT-B/32 | Milliseconds per crop; gives a calibrated-ish score per class |

### Retrieval design: no vector RAG
The corpus is tiny: 30 assets, 8 knowledge docs, 50 service cases, 1,000 events, 300 work orders, 120 data-quality rows. All of it is keyed by `asset_id`, `asset_class` or `issue_code`. So retrieve with **deterministic joins**, not embeddings:

```
asset_id ─► Asset_Master, Current_State, Telemetry (feature summary),
            Alarms_Events (top-k by severity/recency/status),
            Maintenance_History (last N), Data_Quality (all rows for asset)
asset_class ─► Knowledge_Docs DOC-<CLASS>-CORE
issue_code + asset_class ─► Historical_Service_Cases
always ─► DOC-FIELD-SAFETY, DOC-RAG-GUIDE
```

This is cheaper, exact, and explainable ("we looked up these 14 rows"). Say so on the slide: *"Retrieval is a join, not a guess."* It also answers Q-03 (exact evidence IDs) directly. Keep a vector index only as a stretch for free-text questions.

### Where the LLM runs: hybrid, cache is the contract
| Mode | What runs | Wi-Fi |
|---|---|---|
| **Batch (pipeline step `07_demo_cache`)** | Feature extraction + evidence pack + LLM (local Ollama; optionally Claude via Batch API for higher-quality wording) + validator → `cache/diagnosis/ASSET-017.json`, `cache/status/*.json` | Local: none. Claude: only at build time |
| **Demo Mode (default)** | FastAPI serves cached JSON. The browser streams it word by word for effect | Off |
| **Live Mode (toggle)** | Same pipeline, local Ollama only, for a judge's free question | Off |

Recommendation: generate the **shipped cache with the local model**. That makes "model work runs offline" literally true, not just "cached offline". If Claude-written text is better, keep it as a second cache and label it honestly in the UI ("authored offline by Claude, validated locally"). Never call a cloud API during the demo.

---

## 2. Options compared

### 2.1 Local runtimes on Apple silicon
| Runtime | Structured output | Vision | Speed on Mac | Fit |
|---|---|---|---|---|
| **Ollama** | `format: <JSON schema>` (constrained decoding); Pydantic `model_json_schema()` | Yes, `images` field, schema works with images | Same as llama.cpp on GGUF path; MLX preview faster on >32 GB Macs | **Best: one server, simple** |
| llama.cpp `llama-server` | `response_format` / `json_schema` → GBNF; raw GBNF | Yes (mmproj) | Baseline | Good fallback, more flags |
| mlx-lm / mlx-vlm | Via outlines or prompt + validate [UNVERIFIED native schema support] | mlx-vlm: Qwen-VL, Florence-2, Moondream | Usually fastest for Qwen on Mac (~1.2–1.5× llama.cpp) | Good for batch VLM in Python |
| LM Studio | JSON schema in its OpenAI-compatible server [UNVERIFIED for current build] | Yes | MLX or GGUF engines | GUI; fine for teammates, harder to script |

### 2.2 Text models (4–14 B, 16–32 GB Mac)
| Model | Size on disk (Q4) | Notes |
|---|---|---|
| **Qwen3.5 9B** | 6.6–7.6 GB | Mar 2026; reviews say it beats last-gen 30B. Text + image. Has a thinking mode: turn it off for JSON (`think: false`) [UNVERIFIED flag behaviour for 3.5] |
| Qwen3.5 4B | 3.3–4.0 GB | Use on 16 GB laptops or for the 30 one-liners |
| Gemma 4 12B | ~7.6 GB | Jun 2026, encoder-free multimodal, 256K ctx |
| Gemma 4 E4B | ~9.6 GB download | 128K ctx; Ollama default `gemma4` tag |
| Qwen3 8B / Gemma 3 12B / Phi-4 14B / Mistral Small 3.x | 5–9 GB | Still fine if already downloaded; older |

Speed expectation: an 8–9B Q4 model decodes roughly **20–40 tok/s on a base M-series 16 GB Mac** and ~60–100 tok/s on Max chips [UNVERIFIED for your machine: run `ollama run qwen3.5:9b --verbose` once]. A 250-token diagnosis takes 5–15 s. Thirty one-liners at 40 tokens each take about a minute. That is fine for batch.

### 2.3 Crop labelling (VLM vs CLIP)
| Option | Output | Cost/crop | Strength | Weakness |
|---|---|---|---|---|
| **SigLIP 2 zero-shot** | Score per prompt ("a photo of a centrifugal pump", …) | ~10–50 ms | Fast, deterministic, gives a number for "confidence" | Fixed label set; splat renders are blurry |
| **Qwen3.5 4B/9B (Ollama)** | JSON `{label, alt_labels, confidence, visible_cues}` | 2–8 s | Free-form reasoning, explains cues ("flange, motor housing") | Self-reported confidence is not calibrated |
| Moondream 3 Preview (MLX) | Caption, point, detect | ~1–3 s [UNVERIFIED] | Good at "point/detect X" on Mac, 16 GB min | Separate runtime |
| Florence-2 (MLX/MPS) | `<OD>`, `<OPEN_VOCABULARY_DETECTION>`, captions | <1 s | Tiny, detection boxes | Weaker semantics for industrial parts |
| SmolVLM2 | Caption | <1 s | Very small | Weak on niche classes |

**Use both SigLIP and the VLM.** SigLIP ranks the 5 Valmet classes plus distractors ("pipe", "tank", "boiler", "wall", "cable tray", "unknown"). The VLM gets the crop *and* the top-3 SigLIP labels and must pick one or say `unknown`. Show both in the curator. Agreement = high confidence; disagreement = flag for the human. This honours DOC-3D-MAPPING: "Never silently guess identity."

Render 2–3 views per proposal (front, 45°, top) at 384–512 px with a neutral background. The VLM gets all views in one call.

---

## 3. What the xlsx gives us for P-005

### Identity and state
| Field | Value |
|---|---|
| `asset_id` / tag | ASSET-017 / P-005, PROCESS_PUMP |
| Area / context | AREA-03 Utility Island, `utilities` |
| Criticality | A - production critical |
| Installed / last service / interval | 2017-10-04 / 2026-09-19 / 730 days |
| Connectivity | OPC_UA; anchor ANCHOR-017; QR-SYN-0017; NFC-SYN-0017 |
| `health_score` | **44** (lowest of the 6 pumps; P-002 is 45) |
| `condition_state` / `issue_code` | attention_required / **FOULING** |
| `issue_summary` | "Efficiency loss / fouling-like signature" |
| `urgency` / `recommended_next_check` | high / "inspect hydraulic path" |
| `model_confidence` | 0.91 (last_updated 2026-10-08 07:29) |
| Docs | DOC-PROCESS_PUMP-CORE; asset card DOC-ASSET-017.md (listed in RAG_Corpus_Index, **file not in the pack**) |

### Telemetry: 144 samples, 2026-10-05 00:00 → 10-07 23:30, exactly 30 min apart
Valve columns (`position_*`, `stiction_index`, `pneumatic_supply_bar`, `load_for_opening_pct`, `sensor_bias`) are all NaN for pumps. Use the six pump signals.

| Signal | Day 1 mean | Day 3 mean | Linear slope / day | z, last 6 h vs first 12 h | vs healthy peers P-003/P-006 (z of 3-day mean) |
|---|---|---|---|---|---|
| process_flow_pct | 77.18 | **68.71** | **−2.06** | −0.14 | **−1.34** (73.1 vs ~84) |
| motor_current_a | 44.09 | **46.31** | **+1.85** | **+3.0** | **+1.04** (45.2 vs ~42) |
| bearing_temp_c | 57.12 | 57.02 | +0.55 | +2.32 | 0.05 |
| process_pressure_bar | 4.60 | 4.60 | +0.05 | +2.15 | 0.04 |
| vibration_mm_s | 2.06 | 2.10 | +0.01 | 0.36 | −0.01 |
| speed_rpm | 1478.6 | 1478.7 | −0.10 | −0.64 | −0.03 |
| signal_quality_pct | 99.4 | 99.4 | 0 | — | — |

Derived: **flow per amp drops from 1.75 to 1.48 %/A (−15 %) day 1 → day 3**. That is the cleanest single "fouling" number: more current for less flow at constant speed. Vibration is flat, which argues *against* bearing wear or misalignment. Note the flow signal is noisy (std 8.3), so the short-window z is small while the 3-day slope and peer gap are clear. Cite the slope and peer gap, not the 6-hour z, for flow.

Multivariate check (computed in the scratchpad): Mahalanobis distance against healthy peers P-003 + P-006 (6 signals) has a peer 95th percentile of 3.49. P-005's first 12 h average 3.42 (normal). Its last 12 h average **7.28** (≈2× the threshold). IsolationForest trained on the same peers agrees (mean score −0.54 vs −0.45 for peers; lower = more anomalous).

### Events (34 rows for ASSET-017, 2026-09-24 → 10-07)
24 carry `event_code = FOULING`. Status: 21 closed, 7 acknowledged, **6 open**. Open ones: EVT-00248 (INSPECTION_NOTE, high, 10-04), EVT-00914 (DIAGNOSTIC_ALERT, high, 10-04), EVT-00780 (SERVICE_RECOMMENDATION, high, 09-27), EVT-00577 (DIAGNOSTIC_ALERT, medium, 10-03), EVT-00548 (SERVICE_RECOMMENDATION, medium, 10-01), EVT-00262 (INSPECTION_NOTE, low, 09-24). Most recent: EVT-00037 (INSPECTION_NOTE, high, 10-07 15:08, closed).

### Maintenance (11 work orders, 2025-08 → 2026-06)
Mostly seal, bearing, alignment and condition inspections. Results include `no_fault_found` (WO-00011, WO-00012, WO-00230) and `condition_confirmed` (WO-00100, WO-00276). **None is a hydraulic-path / impeller cleaning.** That is a good, honest line: "Previous work targeted seal and bearing; the hydraulic path has no recorded inspection."

### Historical case
**CASE-025**: PROCESS_PUMP, FOULING, "Efficiency loss / fouling-like signature", next check "inspect hydraulic path", severity high, workflow "Confirm asset identity; review trend + events; compare baseline; follow approved safety and maintenance procedures." Fairness note: "Historical synthetic example only." Competing pump cases to rule out: CASE-006/007/028 BEARING_WEAR, CASE-022/026 CAVITATION_RISK, CASE-003/018 SEAL_DEGRADATION.

### Data quality (9 rows, the most of any asset)
DQ-0002 timestamp_jitter high → request_user_confirmation; DQ-0042 duplicate_event → reduce_model_confidence; DQ-0048, DQ-0077, DQ-0085 timestamp_jitter (Telemetry); DQ-0059, DQ-0097 sensor_quality_drop (Telemetry); DQ-0109 missing_value (Alarms_Events); DQ-0113 duplicate_event. **Gotcha:** the flags do not show in the 3-day sample (intervals are exactly 30 min; signal quality is a constant 99.4). Treat DQ rows as metadata that lowers confidence, and say "flag present, not visible in this sample".

### Docs that set the rules
- **DOC-RAG-GUIDE**: name the asset, cite telemetry/events/doc IDs, state confidence, separate observation from hypothesis, propose the next safe verification step. → This *is* our output schema.
- **DOC-FIELD-SAFETY**: do not replace site procedures, LOTO, permits, OEM instructions or qualified staff; recommend verification and escalation, not physical action. → Fixed safety block in every answer.
- **DOC-PROCESS_PUMP-CORE**: use vibration, bearing temp, pressure, flow and motor load together; look for consistent multivariate change; verify locally.
- **Builder_Questions** to name on slides: Q-02 (multivariate degradation), Q-03 (evidence IDs + confidence), Q-06 (lower confidence on poor data), Q-08 (CV/VLM mapping with identity confidence).
- **API_Contract**: `POST /api/copilot/query` → "evidence-backed answer with citations/confidence/safe next check"; `POST /api/work-orders/draft` → "draft only; no real control actions". Implement both routes with these exact names.

---

## 4. Recipe

### 4.1 Pipeline
```
05_bind_metadata ─► 07a_features.py   (pandas: per-asset stats, slopes, z, peer z, Mahalanobis)
                 ─► 07b_evidence.py   (joins → evidence_pack/<asset>.json with stable IDs)
                 ─► 07c_llm.py        (Ollama, format=schema, temp 0, seed fixed)
                 ─► 07d_validate.py   (reject/repair, max 2 retries, else template fallback)
                 ─► cache/diagnosis/ASSET-017.json, cache/status/ASSET-0xx.json
```
Give each computed feature its own ID so it can be cited: `FEAT-017-flow_slope_3d`, `FEAT-017-current_z_6h`, `FEAT-017-flow_per_amp`, `FEAT-017-maha_peers`. The LLM may only cite IDs that appear in the evidence pack.

### 4.2 Diagnosis JSON schema (Pydantic → `format`)
```python
class Claim(BaseModel):
    text: str                      # one sentence
    kind: Literal["observation", "hypothesis"]
    evidence_ids: list[str]        # min 1; FEAT-/EVT-/WO-/CASE-/DOC-/DQ- ids

class Diagnosis(BaseModel):
    asset_id: str                  # must equal requested id
    tag: str
    status: Literal["supported", "insufficient_evidence"]
    headline: str                  # <= 120 chars
    claims: list[Claim]            # 3–6
    likely_issue: str | None       # issue_code from Current_State or a CASE
    ruled_out: list[Claim]         # e.g. bearing wear: vibration flat
    confidence: float              # 0–1, server recomputes and overrides
    confidence_reasons: list[str]  # e.g. "DQ-0059 sensor_quality_drop"
    next_safe_check: str           # verification only
    safety_note_id: Literal["DOC-FIELD-SAFETY"]
    work_order_draft: bool         # true = offer draft, never execute
```
The route one-liner uses a tiny schema: `{asset_id, line (<=90 chars), evidence_ids[1..2]}`.

### 4.3 Prompt skeleton
```
SYSTEM
You are a maintenance diagnostics assistant for a synthetic industrial demo.
Rules (from DOC-RAG-GUIDE and DOC-FIELD-SAFETY):
- Use ONLY the EVIDENCE below. Every claim cites >=1 evidence id from it.
- Label each claim "observation" (directly in data) or "hypothesis" (inference).
- If evidence does not support a diagnosis, set status "insufficient_evidence".
- Recommend verification and escalation only. No physical or control actions.
- Numbers must be copied from EVIDENCE, not computed.
Return JSON matching the schema.

USER
QUESTION: Why is P-005 flagged, and what should the technician check first?
ASSET: {Asset_Master + Current_State row, as compact JSON}
FEATURES: [{id: FEAT-017-flow_slope_3d, value: -2.06, unit: "%/day"}, ...]
PEER_BASELINE: P-003, P-006 means
EVENTS (top 8): [{id: EVT-00914, type: DIAGNOSTIC_ALERT, sev: high, status: open, ts}, ...]
WORK_ORDERS (last 5): [...]
CASES: CASE-025 (match), CASE-006, CASE-022, CASE-003 (alternatives)
DATA_QUALITY: [DQ-0002, DQ-0042, ...]
DOCS: DOC-PROCESS_PUMP-CORE, DOC-FIELD-SAFETY, DOC-RAG-GUIDE (full text, 1 line each)
```
Keep the pack under ~3k tokens. Prefill on a 9B model is fast, so this costs a few seconds.

### 4.4 Validator (server-side, also runs in `/api/copilot/query`)
1. Parse with `Diagnosis.model_validate_json`. Fail → retry with the error message appended (max 2).
2. `asset_id` and `tag` equal the request.
3. Every `evidence_id` is in the pack's ID set. Unknown ID → drop the claim, log it.
4. Every number in claim text (regex `-?\d+(\.\d+)?`) matches a pack value within rounding. Mismatch → drop the claim.
5. At least one observation claim cites a FEAT- or EVT- id. Else force `insufficient_evidence`.
6. A `hypothesis` must cite a CASE- or DOC- id plus one observation id.
7. `next_safe_check` passes a deny-list (`open the valve`, `restart`, `bypass`, `isolate`, `change setpoint`, …) and an allow-list verb (`inspect`, `verify`, `compare`, `confirm`, `escalate`).
8. **Confidence is computed, not trusted:** `conf = model_confidence(0.91) × (1 − 0.05·n_DQ_medium − 0.10·n_DQ_high, floor 0.5) × agreement`, where `agreement` = 1.0 if the feature signature matches the issue_code, else 0.7. P-005 example: 0.91 × (1 − 0.05·8 − 0.10·1 = 0.5) ≈ **0.46**. Show the breakdown. This is Q-06 in one line, and the drop from 0.91 is a great demo moment. Tune the weights so the number is defensible.
9. Always append the fixed DOC-FIELD-SAFETY text from the xlsx (not model text).
10. All retries fail → deterministic template answer built from the pack. The demo never shows an error.

### 4.5 Anomaly features (pandas + numpy + scikit-learn, < 1 s for 30 assets)
- **Baseline window:** first 12 h of the 3-day sample per asset (or the 14-day CSV if Valmet ships it; START_HERE names `telemetry_full_14d_30min.csv`, which is not in our folder).
- **Univariate:** z of the last 6 h mean vs baseline; `np.polyfit` slope per day; rolling 6 h median to damp flow noise.
- **Peer comparison:** z vs the healthy same-class assets (`condition_state == healthy`). With synthetic data this is the strongest signal.
- **Physics ratio:** `flow / current` for pumps (fouling), vibration + bearing temp together (bearing), stiction and |setpoint − actual| for valves.
- **Multivariate:** Mahalanobis vs healthy peers, threshold = peer p95. IsolationForest as a second opinion. Report the per-signal contribution (`(x−μ)ᵀΣ⁻¹` terms) so the copilot can say *which* signals drive the distance.
- **Signature rule table** (explainable, maps features to issue codes):
  | Signature | Issue |
  |---|---|
  | flow ↓, current ↑, vibration flat, speed flat | FOULING |
  | vibration ↑, bearing temp ↑ | BEARING_WEAR / MISALIGNMENT |
  | pressure unstable, flow unstable, vibration ↑ | CAVITATION_RISK |
  | flags from Data_Quality only | insufficient_evidence |
- **Route one-liners:** for the ~3–6 assets near the path, use templates filled from Current_State + the top feature ("CV-004 · watch · stiction +0.8σ vs baseline (FEAT-…)"). Let the LLM rephrase only if the validator passes. Healthy assets get a template line; no LLM call needed.

### 4.6 VLM label call
```python
r = ollama.chat(model="qwen3.5:4b", options={"temperature": 0, "seed": 7},
    format=Label.model_json_schema(),
    messages=[{"role": "user", "images": [front, side, top],
      "content": f"Industrial boiler room. Classify the object in the centre. "
                 f"Options: {classes + distractors}. SigLIP top-3: {top3}. "
                 f"Answer 'unknown' if unsure. Name the visible cues."}])
```
`Label = {label, alt_labels[≤2], confidence, visible_cues[≤4]}`. Store the result in the proposal record. The curator shows it as a suggestion; the human approves (non-negotiable 1).

---

## 5. Risks and gotchas
- **Wi-Fi at the venue.** Pull all models today. Test the full demo with Wi-Fi off and `OLLAMA_HOST` bound to localhost. Check nothing in the web app loads fonts or scripts from a CDN.
- **Thinking tokens.** Qwen3.x and Gemma 4 can emit reasoning before JSON. Disable thinking in the request; schema-constrained decoding should still hold the shape [UNVERIFIED for every model tag].
- **Constrained decoding ≠ correct content.** The schema fixes shape, not truth. The validator (section 4.4) is the real grounding.
- **llama.cpp schema gaps.** Some JSON Schema keywords are ignored silently (numeric bounds on floats, remote `$ref`). Validate again in Python.
- **Memory.** A 9B model + VLM + the three.js tab + Python on a 16 GB Mac is tight. Use the 4B for VLM batch, or run batches one at a time with `keep_alive: 0`.
- **Ollama MLX backend** needs >32 GB and is a preview. Do not enable it on demo day.
- **Self-reported VLM confidence** is not calibrated. Display SigLIP score + VLM label agreement instead.
- **Splat crops are blurry and partly transparent.** Render on a flat mid-grey background; drop crops with too few points; expect "unknown" often. That is a feature: it shows honest uncertainty.
- **Synthetic data quirks.** Some DATA_QUALITY events carry `event_code FOULING`; DQ flags are not visible in the 3-day sample; `recommended_handling` sometimes mismatches `issue_type` (e.g. sensor_quality_drop → deduplicate). Do not over-interpret; mention it once as "we read the flags and down-weighted confidence".
- **Missing files.** DOC-ASSET-0xx.md cards and the 14-day CSV are referenced but not supplied. Generate asset cards ourselves from the sheets and label them "generated".
- **Determinism.** Fix `seed` and `temperature 0`, and cache. A judge's re-run must give the same answer.
- **Cloud-authored cache.** If any cached text came from Claude, say so. Claiming it was local would break the "offline" story under questioning.
- **Speeds quoted here** come from other people's hardware. Measure on the demo laptop.

---

## 6. Sources
- Ollama structured outputs (JSON schema `format`, works with images): https://ollama.com/blog/structured-outputs
- Ollama MLX preview, 0.19, >32 GB, Qwen3.5-35B-A3B only: https://ollama.com/blog/mlx
- Ollama Qwen3.5 library (tags, sizes, text+image, 256K): https://ollama.com/library/qwen3.5
- Ollama Gemma 4 library: https://registry.ollama.ai/library/gemma4
- Gemma releases (Gemma 4 dates, 12B Jun 2026): https://ai.google.dev/gemma/docs/releases
- Qwen3.5 small models overview: https://insiderllm.com/guides/qwen-3-5-small-models-9b-beats-30b/
- Qwen3.5 9B review: https://emelia.io/hub/qwen-35-9b-review
- Ollama vs llama.cpp vs MLX on Mac (2026): https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/
- MLX speed claims (vendor, weigh accordingly): https://www.runanywhere.ai/blog/metalrt-fastest-llm-decode-engine-apple-silicon
- Ollama + Qwen3 structured output in Python/Go: https://www.glukhov.org/post/2025/09/llm-structured-output-with-ollama-in-python-and-go/
- Ollama structured outputs with Pydantic in practice: https://dev.to/jangwook_kim_e31e7291ad98/ollama-structured-outputs-in-practice-getting-type-safe-json-from-local-llms-with-pydantic-m38
- llama.cpp structured output / grammars: https://docs.liquid.ai/deployment/on-device/llama-cpp/structured-output
- MLX-VLM on Apple silicon: https://dzone.com/articles/vision-ai-apple-silicon-guide-mlx-vlm
- vllm-mlx (Qwen3-VL serving on Mac): https://pypi.org/project/vllm-mlx/
- Moondream 3 Preview on Mac (MLX, 16 GB): https://moondream.ai/blog/moondream-station-m3-preview
- Florence-2 MLX conversions: https://huggingface.co/collections/mlx-community/florence-2-6741f3f1459000b8129b09b7
- SigLIP 2 paper: https://arxiv.org/html/2502.14786v1
- SigLIP 2 model card: https://huggingface.co/google/siglip2-so400m-patch14-224-jax
- Claude Message Batches API (offline batch authoring option): https://docs.anthropic.com/en/docs/build-with-claude/batch-processing
- Builder Pack xlsx v4.0: sheets Current_State, Telemetry_Sample_3d, Alarms_Events, Maintenance_History, Historical_Service_Cases, Knowledge_Docs, Data_Quality, Builder_Questions, API_Contract, RAG_Corpus_Index, START_HERE (read-only; values computed 2026-11-06 with pandas)
