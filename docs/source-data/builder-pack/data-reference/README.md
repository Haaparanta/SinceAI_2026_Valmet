# Builder pack: full data reference

Every row of the small sheets, generated from the Excel on 2026-11-06. Dates are converted from Excel serials. For what the columns mean and how to use them, see the [builder pack overview](../README.md).

Contents: [Assets](#asset_master) · [Current state](#current_state) · [Scene anchors](#scene_anchors) · [Evidence per asset](#evidence-per-asset) · [Historical service cases](#historical_service_cases) · [RAG corpus index](#rag_corpus_index)

## Asset_Master

| asset_id | tag | asset_class | area_id | area_name | process_context | criticality | installation_date | last_service_date | service_interval_days | connectivity_profile | qr_id | nfc_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASSET-001 | CV-001 | CONTROL_VALVE | AREA-03 | Utility Island | utilities | A - production critical | 2020-12-16 | 2026-01-15 | 180 | OPC_UA | QR-SYN-0001 | NFC-SYN-0001 |
| ASSET-002 | CV-002 | CONTROL_VALVE | AREA-01 | Stock Preparation | wet_process | B - important | 2023-10-28 | 2026-04-14 | 180 | HART | QR-SYN-0002 | NFC-SYN-0002 |
| ASSET-003 | CV-003 | CONTROL_VALVE | AREA-04 | Chemical Preparation | wet_process | A - production critical | 2018-05-06 | 2026-03-02 | 540 | FOUNDATION_FIELDBUS | QR-SYN-0003 | NFC-SYN-0003 |
| ASSET-004 | CV-004 | CONTROL_VALVE | AREA-02 | Machine Hall | continuous_process | A - production critical | 2017-01-23 | 2026-06-06 | 365 | OPC_UA | QR-SYN-0004 | NFC-SYN-0004 |
| ASSET-005 | CV-005 | CONTROL_VALVE | AREA-02 | Machine Hall | continuous_process | C - standard | 2017-10-16 | 2026-02-15 | 180 | OPC_UA | QR-SYN-0005 | NFC-SYN-0005 |
| ASSET-006 | CV-006 | CONTROL_VALVE | AREA-03 | Utility Island | utilities | B - important | 2019-01-15 | 2025-07-03 | 540 | OPC_UA | QR-SYN-0006 | NFC-SYN-0006 |
| ASSET-007 | CV-007 | CONTROL_VALVE | AREA-01 | Stock Preparation | wet_process | C - standard | 2018-04-20 | 2026-08-13 | 540 | HART | QR-SYN-0007 | NFC-SYN-0007 |
| ASSET-008 | CV-008 | CONTROL_VALVE | AREA-02 | Machine Hall | continuous_process | A - production critical | 2020-05-02 | 2026-05-08 | 540 | OPC_UA | QR-SYN-0008 | NFC-SYN-0008 |
| ASSET-009 | CV-009 | CONTROL_VALVE | AREA-03 | Utility Island | utilities | B - important | 2019-12-26 | 2026-01-27 | 180 | FOUNDATION_FIELDBUS | QR-SYN-0009 | NFC-SYN-0009 |
| ASSET-010 | CV-010 | CONTROL_VALVE | AREA-02 | Machine Hall | continuous_process | B - important | 2020-09-26 | 2025-12-25 | 180 | FOUNDATION_FIELDBUS | QR-SYN-0010 | NFC-SYN-0010 |
| ASSET-011 | CV-011 | CONTROL_VALVE | AREA-04 | Chemical Preparation | wet_process | A - production critical | 2020-03-05 | 2026-01-03 | 180 | OPC_UA | QR-SYN-0011 | NFC-SYN-0011 |
| ASSET-012 | CV-012 | CONTROL_VALVE | AREA-01 | Stock Preparation | wet_process | A - production critical | 2021-12-29 | 2026-02-22 | 180 | SIMULATED_API | QR-SYN-0012 | NFC-SYN-0012 |
| ASSET-013 | P-001 | PROCESS_PUMP | AREA-05 | Water Treatment | utilities | B - important | 2018-08-20 | 2026-02-20 | 540 | OPC_UA | QR-SYN-0013 | NFC-SYN-0013 |
| ASSET-014 | P-002 | PROCESS_PUMP | AREA-04 | Chemical Preparation | wet_process | C - standard | 2018-10-02 | 2025-11-13 | 365 | SIMULATED_API | QR-SYN-0014 | NFC-SYN-0014 |
| ASSET-015 | P-003 | PROCESS_PUMP | AREA-01 | Stock Preparation | wet_process | C - standard | 2018-07-26 | 2026-05-06 | 365 | SIMULATED_API | QR-SYN-0015 | NFC-SYN-0015 |
| ASSET-016 | P-004 | PROCESS_PUMP | AREA-04 | Chemical Preparation | wet_process | A - production critical | 2024-05-16 | 2026-08-07 | 365 | MQTT_EDGE | QR-SYN-0016 | NFC-SYN-0016 |
| ASSET-017 | P-005 | PROCESS_PUMP | AREA-03 | Utility Island | utilities | A - production critical | 2017-10-04 | 2026-09-19 | 730 | OPC_UA | QR-SYN-0017 | NFC-SYN-0017 |
| ASSET-018 | P-006 | PROCESS_PUMP | AREA-02 | Machine Hall | continuous_process | B - important | 2019-01-16 | 2025-06-04 | 540 | MQTT_EDGE | QR-SYN-0018 | NFC-SYN-0018 |
| ASSET-019 | M-001 | ELECTRIC_MOTOR | AREA-02 | Machine Hall | continuous_process | A - production critical | 2019-09-23 | 2025-01-09 | 730 | MQTT_EDGE | QR-SYN-0019 | NFC-SYN-0019 |
| ASSET-020 | M-002 | ELECTRIC_MOTOR | AREA-03 | Utility Island | utilities | B - important | 2017-04-06 | 2024-08-26 | 730 | MQTT_EDGE | QR-SYN-0020 | NFC-SYN-0020 |
| ASSET-021 | M-003 | ELECTRIC_MOTOR | AREA-04 | Chemical Preparation | wet_process | B - important | 2023-08-05 | 2025-01-09 | 730 | OPC_UA | QR-SYN-0021 | NFC-SYN-0021 |
| ASSET-022 | M-004 | ELECTRIC_MOTOR | AREA-01 | Stock Preparation | wet_process | B - important | 2020-10-05 | 2024-11-19 | 540 | SIMULATED_API | QR-SYN-0022 | NFC-SYN-0022 |
| ASSET-023 | M-005 | ELECTRIC_MOTOR | AREA-02 | Machine Hall | continuous_process | C - standard | 2025-01-29 | 2025-08-12 | 365 | MQTT_EDGE | QR-SYN-0023 | NFC-SYN-0023 |
| ASSET-024 | M-006 | ELECTRIC_MOTOR | AREA-01 | Stock Preparation | wet_process | C - standard | 2017-12-11 | 2025-06-12 | 540 | OPC_UA | QR-SYN-0024 | NFC-SYN-0024 |
| ASSET-025 | PT-001 | PRESSURE_TRANSMITTER | AREA-05 | Water Treatment | utilities | A - production critical | 2018-04-01 | 2025-06-30 | 365 | MQTT_EDGE | QR-SYN-0025 | NFC-SYN-0025 |
| ASSET-026 | PT-002 | PRESSURE_TRANSMITTER | AREA-03 | Utility Island | utilities | A - production critical | 2018-12-16 | 2025-08-28 | 540 | OPC_UA | QR-SYN-0026 | NFC-SYN-0026 |
| ASSET-027 | PT-003 | PRESSURE_TRANSMITTER | AREA-04 | Chemical Preparation | wet_process | B - important | 2022-01-15 | 2024-06-22 | 730 | SIMULATED_API | QR-SYN-0027 | NFC-SYN-0027 |
| ASSET-028 | VS-001 | VIBRATION_SENSOR | AREA-04 | Chemical Preparation | wet_process | B - important | 2020-05-01 | 2024-06-30 | 730 | SIMULATED_API | QR-SYN-0028 | NFC-SYN-0028 |
| ASSET-029 | VS-002 | VIBRATION_SENSOR | AREA-04 | Chemical Preparation | wet_process | B - important | 2022-12-28 | 2024-10-08 | 540 | SIMULATED_API | QR-SYN-0029 | NFC-SYN-0029 |
| ASSET-030 | VS-003 | VIBRATION_SENSOR | AREA-04 | Chemical Preparation | wet_process | B - important | 2022-08-10 | 2024-04-09 | 730 | MQTT_EDGE | QR-SYN-0030 | NFC-SYN-0030 |

## Current_State

`last_updated` is the snapshot time (all on 2026-10-08 between 07:20 and 07:44).

| asset_id | tag | health_score | condition_state | issue_code | issue_summary | urgency | recommended_next_check | model_confidence | last_updated | knowledge_doc_id |
|---|---|---|---|---|---|---|---|---|---|---|
| ASSET-001 | CV-001 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.89 | 2026-10-08 07:42 | DOC-CONTROL_VALVE-CORE |
| ASSET-002 | CV-002 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.81 | 2026-10-08 07:41 | DOC-CONTROL_VALVE-CORE |
| ASSET-003 | CV-003 | 52 | degraded | POSITION_DEVIATION | Position tracking deviation | high | verify control and mechanics | 0.81 | 2026-10-08 07:44 | DOC-CONTROL_VALVE-CORE |
| ASSET-004 | CV-004 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.71 | 2026-10-08 07:23 | DOC-CONTROL_VALVE-CORE |
| ASSET-005 | CV-005 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.77 | 2026-10-08 07:39 | DOC-CONTROL_VALVE-CORE |
| ASSET-006 | CV-006 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.88 | 2026-10-08 07:41 | DOC-CONTROL_VALVE-CORE |
| ASSET-007 | CV-007 | 71 | watch | CALIBRATION_DRIFT | Position calibration drift | medium | verify calibration | 0.69 | 2026-10-08 07:36 | DOC-CONTROL_VALVE-CORE |
| ASSET-008 | CV-008 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.84 | 2026-10-08 07:42 | DOC-CONTROL_VALVE-CORE |
| ASSET-009 | CV-009 | 59 | degraded | POSITION_DEVIATION | Position tracking deviation | medium | verify control and mechanics | 0.69 | 2026-10-08 07:38 | DOC-CONTROL_VALVE-CORE |
| ASSET-010 | CV-010 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.87 | 2026-10-08 07:21 | DOC-CONTROL_VALVE-CORE |
| ASSET-011 | CV-011 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.91 | 2026-10-08 07:28 | DOC-CONTROL_VALVE-CORE |
| ASSET-012 | CV-012 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.79 | 2026-10-08 07:24 | DOC-CONTROL_VALVE-CORE |
| ASSET-013 | P-001 | 69 | degraded | MISALIGNMENT | Rotating-equipment alignment signature | medium | inspect alignment | 0.85 | 2026-10-08 07:28 | DOC-PROCESS_PUMP-CORE |
| ASSET-014 | P-002 | 45 | attention_required | CAVITATION_RISK | Hydraulic instability / cavitation-like signature | high | inspect process conditions | 0.68 | 2026-10-08 07:28 | DOC-PROCESS_PUMP-CORE |
| ASSET-015 | P-003 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.93 | 2026-10-08 07:26 | DOC-PROCESS_PUMP-CORE |
| ASSET-016 | P-004 | 72 | watch | SEAL_DEGRADATION | Seal-related degradation signature | medium | inspect for leakage | 0.91 | 2026-10-08 07:27 | DOC-PROCESS_PUMP-CORE |
| ASSET-017 | P-005 | 44 | attention_required | FOULING | Efficiency loss / fouling-like signature | high | inspect hydraulic path | 0.91 | 2026-10-08 07:29 | DOC-PROCESS_PUMP-CORE |
| ASSET-018 | P-006 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.88 | 2026-10-08 07:42 | DOC-PROCESS_PUMP-CORE |
| ASSET-019 | M-001 | 77 | watch | MISALIGNMENT | Coupling/alignment-related vibration pattern | routine | inspect alignment | 0.93 | 2026-10-08 07:21 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-020 | M-002 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.68 | 2026-10-08 07:34 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-021 | M-003 | 81 | watch | MISALIGNMENT | Coupling/alignment-related vibration pattern | routine | inspect alignment | 0.77 | 2026-10-08 07:31 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-022 | M-004 | 69 | degraded | CURRENT_IMBALANCE | Current/load imbalance signature | medium | inspect electrical condition | 0.85 | 2026-10-08 07:25 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-023 | M-005 | 61 | degraded | CURRENT_IMBALANCE | Current/load imbalance signature | medium | inspect electrical condition | 0.75 | 2026-10-08 07:43 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-024 | M-006 | 45 | attention_required | OVERHEATING | Sustained temperature elevation | high | inspect cooling and load | 0.72 | 2026-10-08 07:25 | DOC-ELECTRIC_MOTOR-CORE |
| ASSET-025 | PT-001 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.74 | 2026-10-08 07:41 | DOC-PRESSURE_TRANSMITTER-CORE |
| ASSET-026 | PT-002 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.92 | 2026-10-08 07:41 | DOC-PRESSURE_TRANSMITTER-CORE |
| ASSET-027 | PT-003 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.74 | 2026-10-08 07:40 | DOC-PRESSURE_TRANSMITTER-CORE |
| ASSET-028 | VS-001 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.82 | 2026-10-08 07:41 | DOC-VIBRATION_SENSOR-CORE |
| ASSET-029 | VS-002 | 58 | degraded | MOUNTING_ISSUE | Mounting-quality signature | medium | inspect sensor mounting | 0.74 | 2026-10-08 07:21 | DOC-VIBRATION_SENSOR-CORE |
| ASSET-030 | VS-003 | 96 | healthy | NORMAL | No significant deviation | routine | monitor | 0.93 | 2026-10-08 07:21 | DOC-VIBRATION_SENSOR-CORE |

## Scene_Anchors

Every row also has `identity_methods = asset_id / QR / NFC / manual mapping`, `mapping_status = placeholder_until_valmet_scene_received`, `mapping_confidence = 0.65` and `remap_instruction = "Remap to real scene path and bounds when Valmet splat arrives."`

Bounding-box size is fixed per class:

| Class | bbox x × y × z (m) |
|---|---|
| CONTROL_VALVE | 1.0 × 0.8 × 1.3 |
| PROCESS_PUMP | 1.8 × 1.0 × 1.1 |
| ELECTRIC_MOTOR | 1.4 × 0.9 × 0.9 |
| PRESSURE_TRANSMITTER | 0.35 × 0.25 × 0.5 |
| VIBRATION_SENSOR | 0.15 × 0.15 × 0.12 |

| scene_anchor_id | asset_id | tag | area_id | x_local_m | y_local_m | z_local_m | bbox_x_m | bbox_y_m | bbox_z_m | scene_path |
|---|---|---|---|---|---|---|---|---|---|---|
| ANCHOR-001 | ASSET-001 | CV-001 | AREA-03 | 4.24 | -0.14 | 1.33 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-03/CV-001 |
| ANCHOR-002 | ASSET-002 | CV-002 | AREA-01 | 8.64 | -0.36 | 1.71 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-01/CV-002 |
| ANCHOR-003 | ASSET-003 | CV-003 | AREA-04 | 12.78 | -0.18 | 0.78 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-04/CV-003 |
| ANCHOR-004 | ASSET-004 | CV-004 | AREA-02 | 17.22 | -0.39 | 0.69 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-02/CV-004 |
| ANCHOR-005 | ASSET-005 | CV-005 | AREA-02 | 21.71 | -0.27 | 1.29 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-02/CV-005 |
| ANCHOR-006 | ASSET-006 | CV-006 | AREA-03 | 25.52 | -0.25 | 1.08 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-03/CV-006 |
| ANCHOR-007 | ASSET-007 | CV-007 | AREA-01 | 30.07 | -0.14 | 1.83 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-01/CV-007 |
| ANCHOR-008 | ASSET-008 | CV-008 | AREA-02 | -0.32 | 5.18 | 1.15 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-02/CV-008 |
| ANCHOR-009 | ASSET-009 | CV-009 | AREA-03 | 3.91 | 4.96 | 0.72 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-03/CV-009 |
| ANCHOR-010 | ASSET-010 | CV-010 | AREA-02 | 8.83 | 4.75 | 1.18 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-02/CV-010 |
| ANCHOR-011 | ASSET-011 | CV-011 | AREA-04 | 12.86 | 5.02 | 0.68 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-04/CV-011 |
| ANCHOR-012 | ASSET-012 | CV-012 | AREA-01 | 17.38 | 5 | 1.19 | 1 | 0.8 | 1.3 | /SyntheticPlant/AREA-01/CV-012 |
| ANCHOR-013 | ASSET-013 | P-001 | AREA-05 | 21.33 | 4.99 | 0.93 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-05/P-001 |
| ANCHOR-014 | ASSET-014 | P-002 | AREA-04 | 25.98 | 4.74 | 0.75 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-04/P-002 |
| ANCHOR-015 | ASSET-015 | P-003 | AREA-01 | 30.1 | 5.02 | 1.83 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-01/P-003 |
| ANCHOR-016 | ASSET-016 | P-004 | AREA-04 | 0.11 | 10.14 | 2.15 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-04/P-004 |
| ANCHOR-017 | ASSET-017 | P-005 | AREA-03 | 4.36 | 10.17 | 1.57 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-03/P-005 |
| ANCHOR-018 | ASSET-018 | P-006 | AREA-02 | 8.28 | 10.31 | 0.56 | 1.8 | 1 | 1.1 | /SyntheticPlant/AREA-02/P-006 |
| ANCHOR-019 | ASSET-019 | M-001 | AREA-02 | 13.03 | 10.33 | 1.73 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-02/M-001 |
| ANCHOR-020 | ASSET-020 | M-002 | AREA-03 | 17.26 | 10.52 | 0.47 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-03/M-002 |
| ANCHOR-021 | ASSET-021 | M-003 | AREA-04 | 21.12 | 10.45 | 2.14 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-04/M-003 |
| ANCHOR-022 | ASSET-022 | M-004 | AREA-01 | 25.54 | 10.07 | 1.67 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-01/M-004 |
| ANCHOR-023 | ASSET-023 | M-005 | AREA-02 | 30.39 | 9.86 | 0.98 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-02/M-005 |
| ANCHOR-024 | ASSET-024 | M-006 | AREA-01 | 0.12 | 15.37 | 1.93 | 1.4 | 0.9 | 0.9 | /SyntheticPlant/AREA-01/M-006 |
| ANCHOR-025 | ASSET-025 | PT-001 | AREA-05 | 4.34 | 15.34 | 1.77 | 0.35 | 0.25 | 0.5 | /SyntheticPlant/AREA-05/PT-001 |
| ANCHOR-026 | ASSET-026 | PT-002 | AREA-03 | 8.99 | 15.43 | 1.65 | 0.35 | 0.25 | 0.5 | /SyntheticPlant/AREA-03/PT-002 |
| ANCHOR-027 | ASSET-027 | PT-003 | AREA-04 | 12.63 | 15.49 | 1.25 | 0.35 | 0.25 | 0.5 | /SyntheticPlant/AREA-04/PT-003 |
| ANCHOR-028 | ASSET-028 | VS-001 | AREA-04 | 17.49 | 15.04 | 0.68 | 0.15 | 0.15 | 0.12 | /SyntheticPlant/AREA-04/VS-001 |
| ANCHOR-029 | ASSET-029 | VS-002 | AREA-04 | 21.39 | 15.14 | 0.95 | 0.15 | 0.15 | 0.12 | /SyntheticPlant/AREA-04/VS-002 |
| ANCHOR-030 | ASSET-030 | VS-003 | AREA-04 | 25.91 | 15.45 | 1.22 | 0.15 | 0.15 | 0.12 | /SyntheticPlant/AREA-04/VS-003 |

## Evidence per asset

Counts across `Alarms_Events` (1,000 rows, 2026-09-24 → 2026-10-07), `Maintenance_History` (300 rows, 2025-04-01 → 2026-09-01) and `Data_Quality` (120 rows). "Last WO" is the most recent work order: date, action → result.

| asset | tag | state | events | high | open | work orders | last WO | DQ issues |
|---|---|---|---|---|---|---|---|---|
| ASSET-001 | CV-001 | healthy | 32 | 12 | 8 | 6 | 2026-08-18 planned valve service → no_fault_found | timestamp_jitter×1, duplicate_event×1 |
| ASSET-002 | CV-002 | healthy | 38 | 7 | 12 | 5 | 2025-11-10 visual inspection → follow_up_required | duplicate_event×1 |
| ASSET-003 | CV-003 | degraded | 37 | 8 | 7 | 15 | 2026-08-19 planned valve service → service_completed | duplicate_event×1 |
| ASSET-004 | CV-004 | healthy | 26 | 10 | 6 | 10 | 2026-07-28 planned valve service → follow_up_required | unit_metadata_missing×1, duplicate_event×2, stale_document_link×2, sensor_quality_drop×2, timestamp_jitter×1 |
| ASSET-005 | CV-005 | healthy | 36 | 10 | 8 | 16 | 2026-07-12 planned valve service → condition_confirmed | scene_mapping_low_confidence×2, missing_value×1, unit_metadata_missing×1 |
| ASSET-006 | CV-006 | healthy | 31 | 6 | 9 | 9 | 2026-07-13 planned valve service → follow_up_required | stale_document_link×2, timestamp_jitter×2, sensor_quality_drop×1, scene_mapping_low_confidence×1 |
| ASSET-007 | CV-007 | watch | 37 | 5 | 10 | 12 | 2026-08-15 actuator inspection → follow_up_required | sensor_quality_drop×1, timestamp_jitter×1, scene_mapping_low_confidence×1, missing_value×1, stale_document_link×1 |
| ASSET-008 | CV-008 | healthy | 39 | 10 | 11 | 8 | 2026-05-18 planned valve service → follow_up_required | scene_mapping_low_confidence×1, missing_value×1 |
| ASSET-009 | CV-009 | degraded | 29 | 5 | 5 | 11 | 2026-07-31 visual inspection → adjustment_completed | scene_mapping_low_confidence×1, sensor_quality_drop×3, duplicate_event×1 |
| ASSET-010 | CV-010 | healthy | 32 | 8 | 8 | 8 | 2026-07-25 actuator inspection → adjustment_completed | stale_document_link×1, duplicate_event×3, scene_mapping_low_confidence×1 |
| ASSET-011 | CV-011 | healthy | 42 | 12 | 11 | 12 | 2026-07-02 actuator inspection → follow_up_required | sensor_quality_drop×3, missing_value×1, duplicate_event×1, scene_mapping_low_confidence×1 |
| ASSET-012 | CV-012 | healthy | 33 | 9 | 7 | 6 | 2026-07-24 diagnostic review → service_completed | scene_mapping_low_confidence×1, missing_value×1, timestamp_jitter×1, unit_metadata_missing×1, sensor_quality_drop×1 |
| ASSET-013 | P-001 | degraded | 20 | 3 | 7 | 12 | 2026-06-07 alignment check → service_completed | unit_metadata_missing×1 |
| ASSET-014 | P-002 | attention_required | 39 | 7 | 14 | 9 | 2026-01-18 planned pump service → adjustment_completed | timestamp_jitter×1, stale_document_link×1 |
| ASSET-015 | P-003 | healthy | 28 | 5 | 6 | 11 | 2026-07-29 alignment check → service_completed | timestamp_jitter×3, sensor_quality_drop×2 |
| ASSET-016 | P-004 | watch | 29 | 6 | 8 | 14 | 2026-09-01 seal inspection → condition_confirmed | timestamp_jitter×1, sensor_quality_drop×1, duplicate_event×1, stale_document_link×1, unit_metadata_missing×1 |
| ASSET-017 | P-005 | attention_required | 34 | 13 | 6 | 11 | 2026-06-23 bearing inspection → no_fault_found | timestamp_jitter×4, duplicate_event×2, sensor_quality_drop×2, missing_value×1 |
| ASSET-018 | P-006 | healthy | 41 | 11 | 8 | 8 | 2026-08-04 seal inspection → no_fault_found | unit_metadata_missing×2, scene_mapping_low_confidence×2 |
| ASSET-019 | M-001 | watch | 30 | 9 | 5 | 10 | 2026-08-15 alignment check → condition_confirmed | timestamp_jitter×1, duplicate_event×2, missing_value×1 |
| ASSET-020 | M-002 | healthy | 38 | 10 | 11 | 11 | 2026-05-03 alignment check → adjustment_completed | timestamp_jitter×1 |
| ASSET-021 | M-003 | watch | 34 | 4 | 11 | 7 | 2026-08-10 cooling inspection → adjustment_completed | timestamp_jitter×3, unit_metadata_missing×1 |
| ASSET-022 | M-004 | degraded | 39 | 9 | 11 | 8 | 2026-09-01 electrical condition check → service_completed | unit_metadata_missing×1, stale_document_link×1, timestamp_jitter×1 |
| ASSET-023 | M-005 | degraded | 30 | 10 | 5 | 10 | 2026-08-11 cooling inspection → adjustment_completed | timestamp_jitter×1, duplicate_event×1, unit_metadata_missing×2, stale_document_link×1, scene_mapping_low_confidence×1 |
| ASSET-024 | M-006 | attention_required | 26 | 5 | 5 | 7 | 2026-08-27 vibration inspection → service_completed | stale_document_link×1 |
| ASSET-025 | PT-001 | healthy | 32 | 10 | 9 | 11 | 2026-08-26 signal verification → adjustment_completed | missing_value×2, timestamp_jitter×1, duplicate_event×1 |
| ASSET-026 | PT-002 | healthy | 39 | 13 | 7 | 11 | 2026-04-19 reference comparison → condition_confirmed | timestamp_jitter×1, scene_mapping_low_confidence×1, stale_document_link×1, unit_metadata_missing×2, missing_value×1 |
| ASSET-027 | PT-003 | healthy | 30 | 5 | 6 | 9 | 2026-08-17 reference comparison → follow_up_required | timestamp_jitter×1, sensor_quality_drop×1 |
| ASSET-028 | VS-001 | healthy | 26 | 10 | 8 | 13 | 2026-07-08 sensor replacement assessment → adjustment_completed | scene_mapping_low_confidence×1, sensor_quality_drop×2, timestamp_jitter×1 |
| ASSET-029 | VS-002 | degraded | 34 | 6 | 8 | 11 | 2026-06-03 mounting inspection → follow_up_required | scene_mapping_low_confidence×2, timestamp_jitter×2 |
| ASSET-030 | VS-003 | healthy | 39 | 8 | 8 | 9 | 2026-04-27 mounting inspection → service_completed | missing_value×1, stale_document_link×1, unit_metadata_missing×2, timestamp_jitter×1 |

## Historical_Service_Cases

All 50 rows share the same `safe_evidence_workflow` ("Confirm asset identity; review trend + events; compare baseline; follow approved safety and maintenance procedures.") and `fairness_note` ("Historical synthetic example only."), so those columns are left out.

| case_id | asset_class | historical_issue_code | historical_interpretation | recommended_next_check | severity | knowledge_doc_id |
|---|---|---|---|---|---|---|
| CASE-001 | PRESSURE_TRANSMITTER | SENSOR_DRIFT | Slow measurement drift | verify against reference | high | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-002 | VIBRATION_SENSOR | SENSOR_DRIFT | Baseline drift | verify mounting and reference | medium | DOC-VIBRATION_SENSOR-CORE |
| CASE-003 | PROCESS_PUMP | SEAL_DEGRADATION | Seal-related degradation signature | inspect for leakage | high | DOC-PROCESS_PUMP-CORE |
| CASE-004 | PRESSURE_TRANSMITTER | SIGNAL_DROPOUT | Intermittent signal quality issue | inspect signal path | medium | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-005 | CONTROL_VALVE | SUPPLY_PRESSURE_LOW | Reduced pneumatic supply indication | check supply condition | low | DOC-CONTROL_VALVE-CORE |
| CASE-006 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | high | DOC-PROCESS_PUMP-CORE |
| CASE-007 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | medium | DOC-PROCESS_PUMP-CORE |
| CASE-008 | VIBRATION_SENSOR | MOUNTING_ISSUE | Mounting-quality signature | inspect sensor mounting | medium | DOC-VIBRATION_SENSOR-CORE |
| CASE-009 | PRESSURE_TRANSMITTER | CALIBRATION_DUE | Calibration interval exceeded | schedule calibration | low | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-010 | PRESSURE_TRANSMITTER | CALIBRATION_DUE | Calibration interval exceeded | schedule calibration | low | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-011 | VIBRATION_SENSOR | SENSOR_DRIFT | Baseline drift | verify mounting and reference | high | DOC-VIBRATION_SENSOR-CORE |
| CASE-012 | CONTROL_VALVE | SEAT_LEAKAGE_SUSPECTED | Possible seat leakage signature | plan condition check | medium | DOC-CONTROL_VALVE-CORE |
| CASE-013 | PRESSURE_TRANSMITTER | SENSOR_DRIFT | Slow measurement drift | verify against reference | high | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-014 | CONTROL_VALVE | SUPPLY_PRESSURE_LOW | Reduced pneumatic supply indication | check supply condition | medium | DOC-CONTROL_VALVE-CORE |
| CASE-015 | VIBRATION_SENSOR | MOUNTING_ISSUE | Mounting-quality signature | inspect sensor mounting | medium | DOC-VIBRATION_SENSOR-CORE |
| CASE-016 | PRESSURE_TRANSMITTER | SIGNAL_DROPOUT | Intermittent signal quality issue | inspect signal path | high | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-017 | CONTROL_VALVE | POSITION_DEVIATION | Position tracking deviation | verify control and mechanics | high | DOC-CONTROL_VALVE-CORE |
| CASE-018 | PROCESS_PUMP | SEAL_DEGRADATION | Seal-related degradation signature | inspect for leakage | low | DOC-PROCESS_PUMP-CORE |
| CASE-019 | CONTROL_VALVE | SUPPLY_PRESSURE_LOW | Reduced pneumatic supply indication | check supply condition | low | DOC-CONTROL_VALVE-CORE |
| CASE-020 | PRESSURE_TRANSMITTER | CALIBRATION_DUE | Calibration interval exceeded | schedule calibration | low | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-021 | PRESSURE_TRANSMITTER | SENSOR_DRIFT | Slow measurement drift | verify against reference | low | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-022 | PROCESS_PUMP | CAVITATION_RISK | Hydraulic instability / cavitation-like signature | inspect process conditions | medium | DOC-PROCESS_PUMP-CORE |
| CASE-023 | ELECTRIC_MOTOR | CURRENT_IMBALANCE | Current/load imbalance signature | inspect electrical condition | medium | DOC-ELECTRIC_MOTOR-CORE |
| CASE-024 | ELECTRIC_MOTOR | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | high | DOC-ELECTRIC_MOTOR-CORE |
| CASE-025 | PROCESS_PUMP | FOULING | Efficiency loss / fouling-like signature | inspect hydraulic path | high | DOC-PROCESS_PUMP-CORE |
| CASE-026 | PROCESS_PUMP | CAVITATION_RISK | Hydraulic instability / cavitation-like signature | inspect process conditions | high | DOC-PROCESS_PUMP-CORE |
| CASE-027 | CONTROL_VALVE | ACTUATOR_FRICTION | Actuator mechanical friction trend | inspect actuator | medium | DOC-CONTROL_VALVE-CORE |
| CASE-028 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | high | DOC-PROCESS_PUMP-CORE |
| CASE-029 | PROCESS_PUMP | SEAL_DEGRADATION | Seal-related degradation signature | inspect for leakage | high | DOC-PROCESS_PUMP-CORE |
| CASE-030 | ELECTRIC_MOTOR | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | low | DOC-ELECTRIC_MOTOR-CORE |
| CASE-031 | VIBRATION_SENSOR | SIGNAL_DROPOUT | Intermittent signal quality issue | inspect signal path | low | DOC-VIBRATION_SENSOR-CORE |
| CASE-032 | PROCESS_PUMP | MISALIGNMENT | Rotating-equipment alignment signature | inspect alignment | high | DOC-PROCESS_PUMP-CORE |
| CASE-033 | CONTROL_VALVE | CALIBRATION_DRIFT | Position calibration drift | verify calibration | low | DOC-CONTROL_VALVE-CORE |
| CASE-034 | CONTROL_VALVE | STICTION_TREND | Increasing friction/stiction signature | inspect diagnostics | low | DOC-CONTROL_VALVE-CORE |
| CASE-035 | CONTROL_VALVE | STICTION_TREND | Increasing friction/stiction signature | inspect diagnostics | high | DOC-CONTROL_VALVE-CORE |
| CASE-036 | CONTROL_VALVE | SEAT_LEAKAGE_SUSPECTED | Possible seat leakage signature | plan condition check | low | DOC-CONTROL_VALVE-CORE |
| CASE-037 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | high | DOC-PROCESS_PUMP-CORE |
| CASE-038 | ELECTRIC_MOTOR | CURRENT_IMBALANCE | Current/load imbalance signature | inspect electrical condition | high | DOC-ELECTRIC_MOTOR-CORE |
| CASE-039 | PRESSURE_TRANSMITTER | CALIBRATION_DUE | Calibration interval exceeded | schedule calibration | medium | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-040 | PRESSURE_TRANSMITTER | CALIBRATION_DUE | Calibration interval exceeded | schedule calibration | low | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-041 | ELECTRIC_MOTOR | MISALIGNMENT | Coupling/alignment-related vibration pattern | inspect alignment | low | DOC-ELECTRIC_MOTOR-CORE |
| CASE-042 | VIBRATION_SENSOR | SENSOR_DRIFT | Baseline drift | verify mounting and reference | low | DOC-VIBRATION_SENSOR-CORE |
| CASE-043 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | low | DOC-PROCESS_PUMP-CORE |
| CASE-044 | PROCESS_PUMP | FOULING | Efficiency loss / fouling-like signature | inspect hydraulic path | low | DOC-PROCESS_PUMP-CORE |
| CASE-045 | CONTROL_VALVE | SUPPLY_PRESSURE_LOW | Reduced pneumatic supply indication | check supply condition | medium | DOC-CONTROL_VALVE-CORE |
| CASE-046 | PROCESS_PUMP | MISALIGNMENT | Rotating-equipment alignment signature | inspect alignment | low | DOC-PROCESS_PUMP-CORE |
| CASE-047 | PROCESS_PUMP | SEAL_DEGRADATION | Seal-related degradation signature | inspect for leakage | medium | DOC-PROCESS_PUMP-CORE |
| CASE-048 | PRESSURE_TRANSMITTER | SIGNAL_DROPOUT | Intermittent signal quality issue | inspect signal path | medium | DOC-PRESSURE_TRANSMITTER-CORE |
| CASE-049 | PROCESS_PUMP | CAVITATION_RISK | Hydraulic instability / cavitation-like signature | inspect process conditions | high | DOC-PROCESS_PUMP-CORE |
| CASE-050 | PROCESS_PUMP | BEARING_WEAR | Bearing vibration and temperature degradation | inspect bearing condition | high | DOC-PROCESS_PUMP-CORE |

## RAG_Corpus_Index

Only the eight `core_guidance` texts exist (inside the `Knowledge_Docs` sheet). The 30 `asset_card` files were never delivered.

| doc_id | asset_id | tag | scope | file_name | mime_type | document_role |
|---|---|---|---|---|---|---|
| DOC-ASSET-001 | ASSET-001 | CV-001 | CONTROL_VALVE | DOC-ASSET-001.md | text/markdown | asset_card |
| DOC-ASSET-002 | ASSET-002 | CV-002 | CONTROL_VALVE | DOC-ASSET-002.md | text/markdown | asset_card |
| DOC-ASSET-003 | ASSET-003 | CV-003 | CONTROL_VALVE | DOC-ASSET-003.md | text/markdown | asset_card |
| DOC-ASSET-004 | ASSET-004 | CV-004 | CONTROL_VALVE | DOC-ASSET-004.md | text/markdown | asset_card |
| DOC-ASSET-005 | ASSET-005 | CV-005 | CONTROL_VALVE | DOC-ASSET-005.md | text/markdown | asset_card |
| DOC-ASSET-006 | ASSET-006 | CV-006 | CONTROL_VALVE | DOC-ASSET-006.md | text/markdown | asset_card |
| DOC-ASSET-007 | ASSET-007 | CV-007 | CONTROL_VALVE | DOC-ASSET-007.md | text/markdown | asset_card |
| DOC-ASSET-008 | ASSET-008 | CV-008 | CONTROL_VALVE | DOC-ASSET-008.md | text/markdown | asset_card |
| DOC-ASSET-009 | ASSET-009 | CV-009 | CONTROL_VALVE | DOC-ASSET-009.md | text/markdown | asset_card |
| DOC-ASSET-010 | ASSET-010 | CV-010 | CONTROL_VALVE | DOC-ASSET-010.md | text/markdown | asset_card |
| DOC-ASSET-011 | ASSET-011 | CV-011 | CONTROL_VALVE | DOC-ASSET-011.md | text/markdown | asset_card |
| DOC-ASSET-012 | ASSET-012 | CV-012 | CONTROL_VALVE | DOC-ASSET-012.md | text/markdown | asset_card |
| DOC-ASSET-013 | ASSET-013 | P-001 | PROCESS_PUMP | DOC-ASSET-013.md | text/markdown | asset_card |
| DOC-ASSET-014 | ASSET-014 | P-002 | PROCESS_PUMP | DOC-ASSET-014.md | text/markdown | asset_card |
| DOC-ASSET-015 | ASSET-015 | P-003 | PROCESS_PUMP | DOC-ASSET-015.md | text/markdown | asset_card |
| DOC-ASSET-016 | ASSET-016 | P-004 | PROCESS_PUMP | DOC-ASSET-016.md | text/markdown | asset_card |
| DOC-ASSET-017 | ASSET-017 | P-005 | PROCESS_PUMP | DOC-ASSET-017.md | text/markdown | asset_card |
| DOC-ASSET-018 | ASSET-018 | P-006 | PROCESS_PUMP | DOC-ASSET-018.md | text/markdown | asset_card |
| DOC-ASSET-019 | ASSET-019 | M-001 | ELECTRIC_MOTOR | DOC-ASSET-019.md | text/markdown | asset_card |
| DOC-ASSET-020 | ASSET-020 | M-002 | ELECTRIC_MOTOR | DOC-ASSET-020.md | text/markdown | asset_card |
| DOC-ASSET-021 | ASSET-021 | M-003 | ELECTRIC_MOTOR | DOC-ASSET-021.md | text/markdown | asset_card |
| DOC-ASSET-022 | ASSET-022 | M-004 | ELECTRIC_MOTOR | DOC-ASSET-022.md | text/markdown | asset_card |
| DOC-ASSET-023 | ASSET-023 | M-005 | ELECTRIC_MOTOR | DOC-ASSET-023.md | text/markdown | asset_card |
| DOC-ASSET-024 | ASSET-024 | M-006 | ELECTRIC_MOTOR | DOC-ASSET-024.md | text/markdown | asset_card |
| DOC-ASSET-025 | ASSET-025 | PT-001 | PRESSURE_TRANSMITTER | DOC-ASSET-025.md | text/markdown | asset_card |
| DOC-ASSET-026 | ASSET-026 | PT-002 | PRESSURE_TRANSMITTER | DOC-ASSET-026.md | text/markdown | asset_card |
| DOC-ASSET-027 | ASSET-027 | PT-003 | PRESSURE_TRANSMITTER | DOC-ASSET-027.md | text/markdown | asset_card |
| DOC-ASSET-028 | ASSET-028 | VS-001 | VIBRATION_SENSOR | DOC-ASSET-028.md | text/markdown | asset_card |
| DOC-ASSET-029 | ASSET-029 | VS-002 | VIBRATION_SENSOR | DOC-ASSET-029.md | text/markdown | asset_card |
| DOC-ASSET-030 | ASSET-030 | VS-003 | VIBRATION_SENSOR | DOC-ASSET-030.md | text/markdown | asset_card |
| DOC-CONTROL_VALVE-CORE |  |  | CONTROL_VALVE | DOC-CONTROL_VALVE-CORE.md | text/markdown | core_guidance |
| DOC-PROCESS_PUMP-CORE |  |  | PROCESS_PUMP | DOC-PROCESS_PUMP-CORE.md | text/markdown | core_guidance |
| DOC-ELECTRIC_MOTOR-CORE |  |  | ELECTRIC_MOTOR | DOC-ELECTRIC_MOTOR-CORE.md | text/markdown | core_guidance |
| DOC-PRESSURE_TRANSMITTER-CORE |  |  | PRESSURE_TRANSMITTER | DOC-PRESSURE_TRANSMITTER-CORE.md | text/markdown | core_guidance |
| DOC-VIBRATION_SENSOR-CORE |  |  | VIBRATION_SENSOR | DOC-VIBRATION_SENSOR-CORE.md | text/markdown | core_guidance |
| DOC-FIELD-SAFETY |  |  | ALL | DOC-FIELD-SAFETY.md | text/markdown | core_guidance |
| DOC-RAG-GUIDE |  |  | ALL | DOC-RAG-GUIDE.md | text/markdown | core_guidance |
| DOC-3D-MAPPING |  |  | ALL | DOC-3D-MAPPING.md | text/markdown | core_guidance |
