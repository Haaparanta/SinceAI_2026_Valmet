# S11: Probabilistic Fault Reasoning ("Bayesian Network + Fault Tree Copilot")

**Type:** logic + probability (AI side) · **GPU:** no · **LLM:** narrator only · **Runtime:** inference < 10 ms per asset

**One line:** Build a small Bayesian network / fault tree per asset class from the Excel pack (issue codes ↔ telemetry symptoms ↔ service cases), infer the most likely root cause with a probability, and pick the next inspection step that most reduces uncertainty.

**Bet:** The AI criterion (20%) asks the assistant to "accurately explain" and give "grounded troubleshooting". A probabilistic model gives numbers you can defend ("FOULING 0.71, CAVITATION 0.18, SENSOR fault 0.11 given flow −12% and vibration +30%; check the hydraulic path first because it separates the top two causes"). It pairs with any extraction plan (S1–S9).

---

## Model

```
             ┌──────────── root causes (priors from Historical_Service_Cases counts per asset_class)
             │  BEARING_WEAR · MISALIGNMENT · CAVITATION_RISK · FOULING · SEAL_DEGRADATION · SENSOR_DRIFT …
             ▼
     symptoms (discretised trends from Telemetry_Sample_3d, 72 h)
        vibration_mm_s ↑ · bearing_temp_c ↑ · process_flow_pct ↓ · motor_current_a ↑/≠ · signal_quality ↓ …
             │
     evidence quality: Data_Quality flags + signal_quality_pct → soft evidence (Q-06)
             │
     outputs: P(cause | evidence) · expected-information-gain ranking of next checks
              (next checks come from Current_State.recommended_next_check + service cases)
```

- **Structure:** one hand-written network per asset class (5 classes: control valve, pump, motor, pressure transmitter, vibration sensor), from the class knowledge docs ("use vibration, bearing temperature, pressure, flow and motor load together").
- **Parameters:** priors from case counts (e.g. BEARING_WEAR 8, SENSOR_DRIFT 6, CALIBRATION_DUE 5 …); likelihoods hand-set with simple monotone assumptions, then sanity-checked against the 13 non-healthy assets in `Current_State` (does the model rank the labelled `issue_code` first?). That check is a measurable accuracy number for the slides.
- **Fault tree view:** the same structure shown as an AND/OR tree in the UI for the target device.
- **LLM:** Claude turns the posterior + evidence IDs into the spoken explanation; it cannot change the numbers.

## Components

| Part | Choice |
|---|---|
| Inference | `pgmpy` (installs on Python 3.12), or ~80 lines of hand-written exact inference (networks are tiny) |
| Trend features | pandas rolling windows, ~50 ms total |
| Anomaly backup | per-signal z-score vs. the asset's own 72 h baseline |
| Output contract | `{asset_id, causes:[{code,p,evidence_ids}], next_checks:[{text, info_gain, doc_id}], confidence, dq_warnings}` |

## What it needs

- 1 person with basic probability; ≈ 5–7 h. Plugs into S5's agent as a `diagnose` tool, or into S6's rule layer L4.

## Scoring estimate (AI side only; combine with an extraction plan)

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| AI grounding | 20% | ●●●●● | Quantified, evidence-linked, uncertainty-aware |
| Backend architecture | 15% | ●●●●○ | Small, testable module |

## Risks

- Hand-set likelihoods can look arbitrary: show the validation against the 13 labelled non-healthy assets.
- Telemetry is synthetic and only 3 days: keep features simple (trend direction + magnitude).
