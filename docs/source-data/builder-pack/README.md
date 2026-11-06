# Synthetic Industrial Metaverse Builder Pack (Excel)

Source: [`Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack (1) (2) (1).xlsx`](../../../Source-Data-Do-Not_change/) · version 4.0 · built by Since AI ry · dated 2026-10-08 · 16 sheets

**Everything in it is synthetic.** It has no real customer geometry or process data, no confidential thresholds and no autonomous control instructions. Every row carries `synthetic_record = 1`.

**Full row-by-row tables** (all 30 assets, states, anchors, per-asset evidence counts, all 50 service cases, all 38 RAG docs) are in [data-reference/](data-reference/README.md).

## Contents

- [At a glance](#at-a-glance)
- [How the sheets link together](#how-the-sheets-link-together)
- [Sheet by sheet](#sheet-by-sheet)
- [Telemetry: what the faults look like](#telemetry-what-the-faults-look-like)
- [Choosing the faulty target](#choosing-the-faulty-target)
- [Dossier: P-005](#dossier-p-005-asset-017)
- [Quirks and traps](#quirks-and-traps)
- [Gaps to plan around](#gaps-to-plan-around)
- [Reading the file](#reading-the-file)

## At a glance

| | |
|---|---|
| Assets | 30: 12 control valves, 6 process pumps, 6 electric motors, 3 pressure transmitters, 3 vibration sensors |
| Plant areas | 5: Chemical Preparation (9), Machine Hall (7), Utility Island (6), Stock Preparation (6), Water Treatment (2) |
| Telemetry in the Excel | 4,320 rows: 30 assets × 144 samples every 30 min over 3 days (2026-10-05 00:00 → 2026-10-07 23:30) |
| Full telemetry | 20,160 rows over 14 days in `telemetry_full_14d_30min.csv`, **not delivered** |
| Events | 1,000 (2026-09-24 → 2026-10-07) |
| Work orders | 300 (2025-04-01 → 2026-09-01) |
| Historical service cases | 50 |
| RAG documents | 38 listed; only the 8 core guidance texts are in the Excel |
| Data-quality issues | 120 |
| Snapshot time | `Current_State` updated 2026-10-08 07:21–07:44 |

**Intended user journey** (from `START_HERE`): 3D object → asset identity → current condition → evidence → documentation → explainable AI → safe verification / maintenance workflow.

## How the sheets link together

```
                     ┌──────────────── Scene_Anchors (scene_anchor_id, xyz, bbox, scene_path)
                     │
Asset_Master ── asset_id ──┬── Current_State (health, issue_code, knowledge_doc_id)
 (tag, class,              ├── Telemetry_Sample_3d (30-min signals)
  area, criticality)       ├── Alarms_Events (event_id, event_code)
                           ├── Maintenance_History (work_order_id, knowledge_doc_id)
                           ├── Data_Quality (issue_id, source_sheet)
                           └── RAG_Corpus_Index (DOC-ASSET-0xx asset cards)

asset_class ── Historical_Service_Cases (issue_code → next check)
asset_class ── Knowledge_Docs (DOC-<CLASS>-CORE) + 3 cross-cutting docs (scope ALL)
```

- **`asset_id`** (`ASSET-001`…`ASSET-030`) is the primary key everywhere. **`tag`** (`CV-001`, `P-005`…) is the human name and appears next to it in most sheets.
- **`issue_code`** in `Current_State` matches `event_code` in `Alarms_Events` and `historical_issue_code` in `Historical_Service_Cases`, so one code joins current state, recent evidence and past cases.
- **`knowledge_doc_id`** is always the class core doc (`DOC-PROCESS_PUMP-CORE` etc.).

## Sheet by sheet

### 1. `START_HERE`

The pack's own README, as key/value rows:

| Key | Value (paraphrased) |
|---|---|
| Purpose | A builder-ready synthetic environment for the Industrial Metaverse demonstrator |
| Scale | 30 assets · 20,160 raw telemetry records · 1,000 events · 300 work orders · 38 RAG docs |
| Core journey | 3D object → identity → condition → evidence → docs → explainable AI → safe verification |
| Real Valmet scene | Not received when the pack was built. `Scene_Anchors` is deliberately a replaceable layer; only paths and coordinates need remapping once the splat arrives |
| Interoperability | Designed to work with web, Unreal, Unity, OpenUSD/Omniverse or other 3D stacks |
| Trustworthy AI | Explicit source IDs, confidence, data-quality and mapping-confidence fields let teams separate evidence from hypothesis |
| Safety / IP | All synthetic; no real geometry, process data, confidential thresholds or autonomous field-control instructions |
| Raw ML file | `telemetry_full_14d_30min.csv` holds the full corpus; the Excel holds a 3-day sample |

### 2. `Public_Research`

Nine public sources, each with a "design implication". Columns: `source, topic, design_implication, source_url`. Every link is summarised in [docs/links/](../../links/README.md).

### 3. `Asset_Master` (30 rows)

| Column | Meaning / values |
|---|---|
| `asset_id` | `ASSET-001`…`030`, primary key |
| `tag` | `CV-001…012` valves, `P-001…006` pumps, `M-001…006` motors, `PT-001…003` pressure transmitters, `VS-001…003` vibration sensors |
| `asset_class` | `CONTROL_VALVE`, `PROCESS_PUMP`, `ELECTRIC_MOTOR`, `PRESSURE_TRANSMITTER`, `VIBRATION_SENSOR` |
| `area_id` / `area_name` | `AREA-01` Stock Preparation, `AREA-02` Machine Hall, `AREA-03` Utility Island, `AREA-04` Chemical Preparation, `AREA-05` Water Treatment |
| `process_context` | `wet_process` 15, `utilities` 8, `continuous_process` 7 |
| `criticality` | `A - production critical` 11, `B - important` 13, `C - standard` 6 |
| `installation_date` | Excel date, 2017–2025 (most 2017–2020) |
| `last_service_date` | Excel date, 2025–2026 |
| `service_interval_days` | 180 (7), 365 (6), 540 (10), 730 (7) |
| `connectivity_profile` | `OPC_UA` 11, `SIMULATED_API` 7, `MQTT_EDGE` 7, `FOUNDATION_FIELDBUS` 3, `HART` 2 |
| `scene_anchor_id` | `ANCHOR-0xx`, same number as the asset |
| `qr_id` / `nfc_id` | `QR-SYN-00xx` / `NFC-SYN-00xx`: fake physical identity tags for "scan to identify" flows |
| `data_classification` | always `SYNTHETIC` |

Class × area:

| | Chem. Prep | Machine Hall | Utility Island | Stock Prep | Water Treat. |
|---|---:|---:|---:|---:|---:|
| Control valves | 2 | 4 | 3 | 3 | 0 |
| Pumps | 2 | 1 | 1 | 1 | 1 |
| Motors | 1 | 2 | 1 | 2 | 0 |
| Pressure transmitters | 1 | 0 | 1 | 0 | 1 |
| Vibration sensors | 3 | 0 | 0 | 0 | 0 |
| **Total** | **9** | **7** | **6** | **6** | **2** |

### 4. `Scene_Anchors` (30 rows): the layer we replace

| Column | Meaning |
|---|---|
| `x_local_m, y_local_m, z_local_m` | Placeholder centre in metres on a made-up plant (x −0.3…30.4, y −0.4…15.5, z 0.5…2.2, so z is up here) |
| `bbox_x_m, bbox_y_m, bbox_z_m` | Box size, fixed per class (valve 1.0×0.8×1.3, pump 1.8×1.0×1.1, motor 1.4×0.9×0.9, PT 0.35×0.25×0.5, VS 0.15×0.15×0.12) |
| `scene_path` | USD-style path, e.g. `/SyntheticPlant/AREA-03/P-005` |
| `mapping_status` | always `placeholder_until_valmet_scene_received` |
| `identity_methods` | always `asset_id / QR / NFC / manual mapping` |
| `mapping_confidence` | always `0.65` |
| `remap_instruction` | "Remap to real scene path and bounds when Valmet splat arrives." |

The positions **do not** match the boiler-room scan, which is about 8.6 × 3.5 units in plan with **y up**. Keep the IDs, overwrite the coordinates, boxes and paths with our extracted clusters, and set a real `mapping_confidence` and `mapping_status` (for example `procedural_assignment`). The fixed box sizes are a useful plausibility check when deciding which cluster gets which class.

### 5. `Current_State` (30 rows): picks the faulty target

| Column | Meaning |
|---|---|
| `health_score` | 0–100. Healthy assets are all exactly 96 |
| `condition_state` | `healthy` 17, `watch` 4, `degraded` 6, `attention_required` 3 |
| `issue_code` / `issue_summary` | e.g. `FOULING` / "Efficiency loss / fouling-like signature" |
| `urgency` | `routine`, `medium`, `high` |
| `recommended_next_check` | short action, e.g. "inspect hydraulic path" |
| `model_confidence` | 0.68–0.93 |
| `knowledge_doc_id` | class core doc |

All 13 non-healthy assets:

| Tag | Asset | Class | Area | Crit. | Health | State | Issue | Urgency | Next check | Conf. |
|---|---|---|---|---|---:|---|---|---|---|---:|
| **P-005** | ASSET-017 | pump | Utility Island | A | **44** | attention_required | FOULING | high | inspect hydraulic path | 0.91 |
| P-002 | ASSET-014 | pump | Chemical Prep | C | 45 | attention_required | CAVITATION_RISK | high | inspect process conditions | 0.68 |
| M-006 | ASSET-024 | motor | Stock Prep | C | 45 | attention_required | OVERHEATING | high | inspect cooling and load | 0.72 |
| CV-003 | ASSET-003 | valve | Chemical Prep | A | 52 | degraded | POSITION_DEVIATION | high | verify control and mechanics | 0.81 |
| VS-002 | ASSET-029 | vib. sensor | Chemical Prep | B | 58 | degraded | MOUNTING_ISSUE | medium | inspect sensor mounting | 0.74 |
| CV-009 | ASSET-009 | valve | Utility Island | B | 59 | degraded | POSITION_DEVIATION | medium | verify control and mechanics | 0.69 |
| M-005 | ASSET-023 | motor | Machine Hall | C | 61 | degraded | CURRENT_IMBALANCE | medium | inspect electrical condition | 0.75 |
| P-001 | ASSET-013 | pump | Water Treatment | B | 69 | degraded | MISALIGNMENT | medium | inspect alignment | 0.85 |
| M-004 | ASSET-022 | motor | Stock Prep | B | 69 | degraded | CURRENT_IMBALANCE | medium | inspect electrical condition | 0.85 |
| CV-007 | ASSET-007 | valve | Stock Prep | C | 71 | watch | CALIBRATION_DRIFT | medium | verify calibration | 0.69 |
| P-004 | ASSET-016 | pump | Chemical Prep | A | 72 | watch | SEAL_DEGRADATION | medium | inspect for leakage | 0.91 |
| M-001 | ASSET-019 | motor | Machine Hall | A | 77 | watch | MISALIGNMENT | routine | inspect alignment | 0.93 |
| M-003 | ASSET-021 | motor | Chemical Prep | B | 81 | watch | MISALIGNMENT | routine | inspect alignment | 0.77 |

### 6. `Telemetry_Sample_3d` (4,320 rows)

| Column | Unit | Filled for |
|---|---|---|
| `timestamp` | Excel datetime, every 30 min | all |
| `asset_id, tag, asset_class, area_id` | keys | all |
| `process_pressure_bar` | bar | valves, pumps, pressure transmitters |
| `process_flow_pct` | % of nominal | valves, pumps |
| `position_setpoint_pct`, `position_actual_pct` | % open | valves |
| `pneumatic_supply_bar` | bar | valves |
| `stiction_index` | index | valves |
| `load_for_opening_pct` | % | valves |
| `vibration_mm_s` | mm/s RMS | pumps, motors, vibration sensors |
| `bearing_temp_c` | °C | pumps, motors |
| `motor_current_a` | A | pumps, motors |
| `speed_rpm` | rpm | pumps, motors |
| `signal_quality_pct` | % | all |
| `sensor_bias` | — | pressure transmitters, vibration sensors |
| `source_profile` | always `simulated_30min_stream` | all |

Ranges by class (min / mean / max over the 3 days):

| Signal | Valves | Pumps | Motors | PTs | VSs |
|---|---|---|---|---|---|
| pressure (bar) | 4.57 / 5.20 / 5.92 | 3.68 / 4.52 / 5.11 | — | 4.52 / 5.00 / 5.54 | — |
| flow (%) | 43.6 / 58.0 / 73.6 | 55.5 / 81.5 / 100.1 | — | — | — |
| setpoint (%) | 19.7 / 49.5 / 84.2 | — | — | — | — |
| actual position (%) | 19.2 / 50.7 / 91.3 | — | — | — | — |
| supply (bar) | 5.53 / 5.80 / 6.16 | — | — | — | — |
| stiction index | 6.37 / 8.50 / 10.31 | — | — | — | — |
| load for opening (%) | 22.9 / 31.0 / 39.3 | — | — | — | — |
| vibration (mm/s) | — | 1.32 / 2.62 / 5.98 | 1.30 / 2.74 / 5.78 | — | 1.59 / 2.62 / 4.80 |
| bearing temp (°C) | — | 51.4 / 57.6 / 68.2 | 48.0 / 55.4 / 78.0 | — | — |
| current (A) | — | 35.6 / 42.9 / 51.9 | 31.5 / 40.5 / 52.7 | — | — |
| speed (rpm) | — | 1460 / 1480 / 1503 | 1470 / 1485 / 1502 | — | — |
| signal quality (%) | 99.5 (constant) | 99.4 (constant) | 99.6 (constant) | 99.8 (constant) | 99.7 (constant) |

### 7. `Alarms_Events` (1,000 rows)

Columns: `event_id, timestamp, asset_id, tag, area_name, event_type, severity, event_code, description, source, status`.

| Field | Distribution |
|---|---|
| `event_type` | SERVICE_RECOMMENDATION 180 · INSPECTION_NOTE 177 · DATA_QUALITY 172 · DIAGNOSTIC_ALERT 167 · CONDITION_CHANGE 160 · WORK_ORDER_CREATED 144 |
| `severity` | medium 487 · low 267 · high 246 |
| `event_code` | NORMAL_CHECK 245 · TREND_UPDATE 237 · MINOR_DEVIATION 222 · CURRENT_IMBALANCE 53 · MISALIGNMENT 52 · POSITION_DEVIATION 50 · CAVITATION_RISK 29 · MOUNTING_ISSUE 27 · FOULING 24 · CALIBRATION_DRIFT 23 · SEAL_DEGRADATION 21 · OVERHEATING 17 |
| `source` | edge_monitor 257 · field_user 254 · mobile_app 248 · analytics_service 241 |
| `status` | closed 488 · acknowledged 267 · open 245 |

Fault codes appear only on assets that have that issue in `Current_State`, so the events are consistent evidence for the copilot. `description` is the same filler sentence on every row; cite events by `event_id` + `event_code` + time.

### 8. `Maintenance_History` (300 work orders)

Columns: `work_order_id, asset_id, tag, area_name, opened_at, action, maintenance_type, priority, result, duration_h, downtime_h, role, knowledge_doc_id`.

| Field | Distribution |
|---|---|
| `maintenance_type` | inspection 87 · preventive 75 · predictive 74 · corrective 64 |
| `priority` | medium 159 · low 80 · high 61 |
| `result` | adjustment_completed 71 · service_completed 62 · follow_up_required 61 · condition_confirmed 56 · no_fault_found 50 |
| `role` | field_technician 112 · reliability_engineer 100 · automation_specialist 88 |
| `action` (top) | calibration verification 32 · planned valve service 29 · actuator inspection 27 · bearing inspection 25 · alignment check 25 · visual inspection 22 · signal verification 21 · seal inspection 19 · … |
| `duration_h` / `downtime_h` | mean 4.4 h / 1.5 h |

This is also the schema for `POST /api/work-orders/draft`: a copilot draft should fill `action`, `maintenance_type`, `priority`, `role` and `knowledge_doc_id`.

### 9. `Historical_Service_Cases` (50 rows)

Per asset class: `historical_issue_code` → `historical_interpretation` → `recommended_next_check` → `severity`, plus a `safe_evidence_workflow` that is identical on every row:

> Confirm asset identity; review trend + events; compare baseline; follow approved safety and maintenance procedures.

| Class | Cases | Issue codes |
|---|---:|---|
| PROCESS_PUMP | 17 | BEARING_WEAR 6, SEAL_DEGRADATION 4, CAVITATION_RISK 3, FOULING 2, MISALIGNMENT 2 |
| PRESSURE_TRANSMITTER | 11 | CALIBRATION_DUE 5, SENSOR_DRIFT 3, SIGNAL_DROPOUT 3 |
| CONTROL_VALVE | 11 | SUPPLY_PRESSURE_LOW 4, STICTION_TREND 2, SEAT_LEAKAGE_SUSPECTED 2, ACTUATOR_FRICTION 1, CALIBRATION_DRIFT 1, POSITION_DEVIATION 1 |
| VIBRATION_SENSOR | 6 | SENSOR_DRIFT 3, MOUNTING_ISSUE 2, SIGNAL_DROPOUT 1 |
| ELECTRIC_MOTOR | 5 | BEARING_WEAR 2, CURRENT_IMBALANCE 2, MISALIGNMENT 1 |

Every current fault has at least one matching historical case except motor `OVERHEATING` (M-006), which the copilot will have to reason about from `DOC-ELECTRIC_MOTOR-CORE` alone. Several codes here (BEARING_WEAR, SENSOR_DRIFT, SIGNAL_DROPOUT, STICTION_TREND, SEAT_LEAKAGE_SUSPECTED, SUPPLY_PRESSURE_LOW, CALIBRATION_DUE, ACTUATOR_FRICTION) do not occur in the current state. They are useful as "what else could it be" alternatives in a diagnosis. All 50 rows are in [data-reference](data-reference/README.md#historical_service_cases).

### 10. `Knowledge_Docs` (8 rows): the only document text in the pack

| doc_id | Scope | Content (paraphrased) |
|---|---|---|
| DOC-CONTROL_VALVE-CORE | CONTROL_VALVE | Judge position, controller diagnostics, pneumatic condition, process context and service history together. Stiction, position deviation, abnormal load, supply pressure and device alerts are reasons to investigate, not proof on their own. |
| DOC-PROCESS_PUMP-CORE | PROCESS_PUMP | Combine vibration, bearing temperature, pressure, flow and motor load. Look for consistent change across several variables, and verify on site before maintenance. |
| DOC-ELECTRIC_MOTOR-CORE | ELECTRIC_MOTOR | Use vibration, bearing temperature, current/load and operating history. Prefer trends over single threshold crossings. |
| DOC-PRESSURE_TRANSMITTER-CORE | PRESSURE_TRANSMITTER | Check continuity, drift and signal quality; compare with process context or a reference measurement. |
| DOC-VIBRATION_SENSOR-CORE | VIBRATION_SENSOR | Check signal stability, drift, gaps and mounting. Poor sensor quality should lower confidence in anything downstream. |
| **DOC-FIELD-SAFETY** | ALL | The assistant must never replace site procedures, lockout/tagout, permits, OEM instructions or qualified staff. It recommends verification and escalation, never autonomous physical action. |
| **DOC-RAG-GUIDE** | ALL | Response contract: name the asset; cite telemetry, event and doc IDs; state confidence; separate observation from hypothesis; propose the next safe verification step. |
| **DOC-3D-MAPPING** | ALL | Map visible objects to stable asset IDs with explicit confidence. Mapping may use scene hierarchy, annotation, QR/NFC or computer vision. Never silently guess identity. |

The three bold docs are effectively the rubric for scoring criterion 3 (AI grounding). Build the copilot's system prompt and output schema directly from them.

### 11. `RAG_Corpus_Index` (38 rows)

Columns: `doc_id, asset_id, tag, scope, file_name, mime_type, document_role`.

- 30 × `asset_card`: `DOC-ASSET-001.md` … `DOC-ASSET-030.md`, one per asset, `text/markdown`.
- 8 × `core_guidance`: the eight `Knowledge_Docs` above.
- The `.md` files themselves were **not delivered**.

### 12. `Data_Quality` (120 rows)

Columns: `issue_id, asset_id, tag, issue_type, severity, source_sheet, recommended_handling`.

| issue_type | Count | Typical source sheets |
|---|---:|---|
| timestamp_jitter | 29 | Telemetry, Scene_Anchors, Alarms_Events |
| sensor_quality_drop | 19 | Telemetry, Knowledge_Docs |
| duplicate_event | 17 | Scene_Anchors, Alarms_Events, Knowledge_Docs |
| scene_mapping_low_confidence | 16 | Alarms_Events, Scene_Anchors |
| unit_metadata_missing | 15 | Alarms_Events, Telemetry, Knowledge_Docs |
| stale_document_link | 13 | Knowledge_Docs, Telemetry |
| missing_value | 11 | Alarms_Events, Scene_Anchors |

Severity: medium 65 · high 28 · low 27. Handling: `flag_for_review` 28 · `request_user_confirmation` 26 · `deduplicate` 24 · `interpolate_if_safe` 22 · `reduce_model_confidence` 20.

Issue type, source sheet and handling are combined at random (a `duplicate_event` on `Scene_Anchors`, for instance), so treat the sheet as "this asset has N open quality flags", not as a precise defect list. A simple, defensible rule: lower the copilot's stated confidence by a fixed step per high-severity DQ issue on the cited asset, and say so in the answer. That covers Builder Q-06.

### 13. `Builder_Questions` (10)

| ID | Question | Focus | Priority | Maps to scoring |
|---|---|---|---|---|
| Q-01 | Identify a device in 3D and show current state, recent evidence and documents | 3D mapping + UX | P0 | 1, 2 |
| Q-02 | Detect emerging degradation from multivariate time series | anomaly detection | P0 | 3 |
| Q-03 | Explain every diagnosis with exact evidence IDs and confidence | explainability + RAG | P0 | 3 |
| Q-04 | Prioritise work by condition, criticality and uncertainty | prioritisation | P1 | 3 |
| Q-05 | 3D object → evidence → service case → work-order draft on mobile/tablet | field workflow | P0 | 3, 5 |
| Q-06 | Lower confidence when sensor or mapping quality is poor | trustworthy AI | P0 | 3 |
| Q-07 | Swap synthetic feeds for OPC UA / MQTT / API without redesign | architecture | P1 | 4 |
| Q-08 | Upgrade scene mapping to CV/VLM recognition, keep identity confidence | computer vision | P2 | 1 |
| Q-09 | Stay portable across web, OpenUSD/Omniverse, Unity, Unreal | interoperability | P1 | 4 |
| Q-10 | Package evidence for remote expert collaboration | remote support | P1 | 5 |

### 14. `API_Contract` (suggested routes)

| Method | Route | Purpose | Backed by |
|---|---|---|---|
| GET | `/api/assets` | hierarchy, scene anchor, criticality | Asset_Master |
| GET | `/api/assets/{id}` | identity, current state, docs | Asset_Master + Current_State |
| GET | `/api/assets/{id}/telemetry` | time-series evidence | Telemetry CSV |
| GET | `/api/assets/{id}/events` | recent alarms/events | Alarms_Events |
| GET | `/api/assets/{id}/documents` | RAG-ready knowledge | RAG_Corpus_Index |
| GET | `/api/scene/anchors` | 3D mapping and confidence | Scene_Anchors |
| POST | `/api/copilot/query` | answer with citations, confidence and a safe next check | all |
| POST | `/api/work-orders/draft` | draft only, no real control actions | Maintenance_History schema |

A route for proximity queries is not listed. We will need one such as `GET /api/scene/nearby?pos=x,y,z&r=2.0`.

### 15. `Dashboard`

| KPI | Value | | Class | Assets | Avg health | Health < 70 |
|---|---:|---|---|---:|---:|---:|
| Assets | 30 | | CONTROL_VALVE | 12 | 87.2 | 2 |
| Raw telemetry records | 20,160 | | ELECTRIC_MOTOR | 6 | 71.5 | 3 |
| Telemetry sample rows | 4,320 | | PRESSURE_TRANSMITTER | 3 | 96.0 | 0 |
| Events | 1,000 | | PROCESS_PUMP | 6 | 70.3 | 3 |
| Historical work orders | 300 | | VIBRATION_SENSOR | 3 | 83.3 | 1 |
| RAG documents | 38 | | | | | |
| Data quality cases | 120 | | | | | |

### 16. `Change_Log`

| Version | Date | Owner | Change |
|---|---|---|---|
| 4.0 | 2026-10-08 | Since AI ry | Built the research-informed pack with a replaceable 3D mapping layer, correlated telemetry, events, history, RAG corpus and trustworthy-AI metadata |
| 4.0 | 2026-10-08 | Since AI ry | Split raw telemetry into a CSV; kept a 3-day sample in Excel |
| 4.0 | 2026-10-08 | Since AI ry | Confirmed no real Valmet customer data and no autonomous maintenance-control instructions |

## Telemetry: what the faults look like

Mean of the first 24 hours vs the last 24 hours of the 3-day sample. Healthy assets of the same class stay flat, so each fault has a clear signature the copilot can cite.

| Tag | Issue | Signature (day 1 → day 3 mean) |
|---|---|---|
| **P-005** | FOULING | flow 77.2 → **68.7 %**, current 44.1 → **46.3 A**; vibration, bearing temp and pressure flat |
| P-002 | CAVITATION_RISK | vibration 2.42 → **4.57 mm/s**, flow 83.1 → **76.2 %**, pressure 4.52 → **4.04 bar** |
| P-001 | MISALIGNMENT | vibration 2.75 → **5.10 mm/s**, current 43.0 → 45.1 A |
| P-004 | SEAL_DEGRADATION | bearing temp 58.6 → **63.1 °C**, pressure 4.54 → 4.35 bar |
| M-006 | OVERHEATING | bearing temp 61.1 → **73.8 °C**, current 39.3 → 41.5 A |
| M-001 / M-003 | MISALIGNMENT | vibration ~4.0 → **~5.2 mm/s** |
| M-004 / M-005 | CURRENT_IMBALANCE | current 43.1 → **46.0 A** / 41.8 → **46.3 A** |
| CV-003 | POSITION_DEVIATION | actual − setpoint gap grows from ~2 to **~6.4 %** |
| CV-009 | POSITION_DEVIATION | gap grows from ~3 to **~7.4 %** |
| CV-007 | CALIBRATION_DRIFT | gap grows from ~2.7 to **~5.0 %** |
| VS-002 | MOUNTING_ISSUE | vibration 3.30 → **4.41 mm/s** |
| healthy references | — | e.g. P-003 vibration 2.10 → 2.14, P-006 flow 84.1 → 83.9, CV-001 gap < 0.1 % |

Healthy pump baseline: flow ≈ 84 %, vibration ≈ 2.1 mm/s, bearing ≈ 57 °C, current ≈ 42 A. Healthy motor baseline: vibration ≈ 1.8 mm/s, bearing ≈ 53 °C, current ≈ 38 A, 1,485 rpm.

## Choosing the faulty target

| Candidate | Why pick it | Why not |
|---|---|---|
| **P-005 (recommended)** | Lowest health (44), the only A-critical asset in `attention_required`, high urgency, highest confidence (0.91), clean two-signal signature, 13 high-severity events | Signature is subtle (flow, current) rather than dramatic |
| M-006 | Dramatic, easy-to-explain signal (+12 °C bearing temperature) | C-standard criticality, confidence 0.72 |
| P-002 | Three signals move at once | C-standard, confidence only 0.68 |

Whichever is chosen, keep 1–2 `watch` / `degraded` assets along the route so the proximity display shows a mix of colours, not just green.

## Dossier: P-005 (ASSET-017)

Everything the copilot needs for the recommended target, in one place.

| | |
|---|---|
| Identity | Process pump P-005, ASSET-017, Utility Island (AREA-03), process context `utilities`, installed 2017-10-04 |
| Criticality / connectivity | A – production critical · OPC_UA · QR-SYN-0017 / NFC-SYN-0017 |
| Service | last service 2026-09-19, interval 730 days |
| Current state | health 44, `attention_required`, `FOULING`: "Efficiency loss / fouling-like signature", urgency high, next check "inspect hydraulic path", model confidence 0.91 |
| Knowledge | `DOC-PROCESS_PUMP-CORE`, asset card `DOC-ASSET-017` (to be generated) |
| Events | 34 in total, 13 high, 6 still open. Recent FOULING events include EVT-00037 (INSPECTION_NOTE, high, 2026-10-07 15:08), EVT-00375 (CONDITION_CHANGE, high, 10-07 10:58), EVT-00313 (SERVICE_RECOMMENDATION, 10-07 06:37), EVT-00248 (INSPECTION_NOTE, high, **open**, 10-04 18:29) |
| Work orders | 11. Most recent: WO-00012 bearing inspection → no_fault_found (2026-06-23); WO-00260 seal inspection → service_completed (2026-05-15); WO-00267 condition inspection → service_completed (2026-04-12) |
| Data quality | 9 flags: timestamp_jitter × 4, duplicate_event × 2, sensor_quality_drop × 2, missing_value × 1 |
| Telemetry evidence | flow down ~11 % and current up ~5 % over 3 days, vibration and bearing temperature flat. Consistent with a hydraulic restriction, not a mechanical bearing problem; the June bearing inspection found no fault, which supports that |
| Matching past cases | `FOULING` cases for PROCESS_PUMP in `Historical_Service_Cases` (next check: inspect hydraulic path) |

A grounded answer following `DOC-RAG-GUIDE` would: name P-005; cite the flow/current trend and the event IDs; state ~0.91 confidence lowered for the open DQ flags; label "fouling" as a hypothesis; rule out bearing wear using the flat vibration and WO-00012; propose inspecting the hydraulic path (strainer, impeller, suction line) under site procedures and LOTO per `DOC-FIELD-SAFETY`; and offer a draft work order.

## Quirks and traps

- **Excel dates are serial numbers.** `46303` = 2026-10-08. Convert with `datetime(1899,12,30) + timedelta(days=serial)`.
- **Inline strings.** The workbook has almost no shared strings; cell text is stored inline (`t="str"`) under an `x:` XML namespace. `openpyxl` and `pandas` handle this fine. Hand-written XML parsers must handle the namespace prefix.
- **Sparse rows.** Empty telemetry cells are omitted from the XML. Read by column letter or header name, never by position.
- **Constant columns.** `signal_quality_pct` is constant per class and `sensor_bias` is always 0, so `sensor_quality_drop` exists only as a DQ flag, not in the signal itself.
- **Health 96 = healthy.** Every healthy asset has exactly 96.
- **Filler text.** `Alarms_Events.description` is the same sentence on all 1,000 rows.
- **Different axes.** `Scene_Anchors` uses z-up metres; the PLY scan is y-up with unverified scale.

## Gaps to plan around

1. **The scan contains more objects than the pack has assets.** Scoring rewards framing *many* objects, but there are only 30 asset rows. Frame everything we can find; give the 30 IDs to the most equipment-like clusters (pumps, vessels, valves on pipes, cabinets) and label the rest generically (pipe, tank, cabinet, shelf) with `mapping_status = unmapped` and no invented telemetry.
2. **No 14-day CSV.** Use the 3-day sample and say so in the technical note.
3. **No asset-card Markdown.** Generate `DOC-ASSET-0xx.md` from the sheets, keeping the IDs from `RAG_Corpus_Index` so citations match.
4. **Placeholder coordinates.** Discard `Scene_Anchors` x/y/z and bbox; keep the IDs and the per-class box sizes as a sanity check.

## Reading the file

```python
import pandas as pd
path = "Source-Data-Do-Not_change/Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack (1) (2) (1).xlsx"
sheets = pd.read_excel(path, sheet_name=None)   # dict of 16 DataFrames
assets = sheets["Asset_Master"].merge(sheets["Current_State"], on=["asset_id", "tag", "asset_class"])
tele = sheets["Telemetry_Sample_3d"]
tele["timestamp"] = pd.to_datetime(tele["timestamp"], unit="D", origin="1899-12-30")
```
