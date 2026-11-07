# Valmet Condition and Runnability Monitoring Services

| | |
|---|---|
| URL | https://www.valmet.com/automation/services/condition-monitoring-services/ |
| Page title | "Valmet Condition and Runnability Monitoring Services" (H1: "Keeping machines in top condition") |
| Publisher / date | Valmet · no publication date (footer © 2026) |
| Pack's design implication | Vibration monitoring, analysis and diagnosis |
| Read | 2026-11-06. The body was read through an extracted summary (page text buried under the site menu). No figures appear on the page |

## Page structure

1. Keeping machines in top condition
2. Valmet Condition and Runnability Monitoring
3. Prevention drives productivity
4. From turnkey monitoring to targeted problem solving
5. Our condition monitoring services
6. Related references
7. Condition monitoring offering

## Section by section

### 1–2. Keeping machines in top condition

Valmet's condition and runnability monitoring covers **audits, planning, analysis and diagnosis, and specialist support** for pulp, board, paper, tissue and energy production. Three benefits: safer maintenance planning, higher process availability through proactive analysis, better maintenance efficiency through skilled people and spare parts.

### 3. Prevention drives productivity

Preventing unplanned downtime avoids lost production and repair cost, and protects productivity through reliability and availability. Valmet experts analyse problems remotely or on site, across whole processes. Standard methods, **vibration monitoring** and **lubrication monitoring**, are judged by their **effect on process performance**, because interactions between machines cause disturbances. The aim is to keep quality-critical components running optimally.

### 4. From turnkey monitoring to targeted problem solving

- Customers can buy a full turnkey programme or a targeted fix, tailored by site, process area or machine.
- System-wide options include Valmet online measurement solutions and system audits.
- Valmet helps plan which monitoring methods to use.
- Analysis and diagnosis ranges from remote expert support to regular online or offline monitoring done by Valmet.
- Specialist services handle **bearing and gear wear** and full-system online vibration monitoring.
- Training lets the customer's own operators take over monitoring tasks.

### 5. The four services

| Service | Purpose |
|---|---|
| Condition Based Maintenance Audit | assess the current maintenance strategy and monitoring coverage |
| Condition Monitoring Planning | decide what to monitor, how and how often |
| Analysis and Diagnosis | interpret measurements, find causes, recommend actions |
| Specialist Services | deep dives: bearings, gears, system-wide vibration |

### 6. Customer references

| Customer | Story |
|---|---|
| UPM Lappeenranta Biorefinery | first-of-its-kind plant making renewable diesel and naphtha from tall oil; uses advanced condition monitoring for reliability |
| "Beyond mechanical condition monitoring for pulp & paper" | article on reviewing maintenance strategy to cut cost and raise availability |
| Metsä Group bioproduct mill (Finland) | chose **Valmet DNA Machine Monitoring** as part of a mill-wide DNA automation system; remote diagnostics supported predictive maintenance |
| Anhui Shanying | a Roll Service Agreement reduced unplanned downtime and corrective maintenance |

### 7. Offering cards

Online condition monitoring · Portable (route-based) condition monitoring · Vibration sensors · Services.

## Glossary

- **Runnability**: how smoothly a paper/board machine runs without breaks or disturbances.
- **Online vs portable/route-based monitoring**: permanently wired sensors streaming data vs a technician walking a route with a handheld analyser.
- **Valmet DNA**: Valmet's distributed control system (DCS); *DNA Machine Monitoring* is its condition-monitoring module.

## Relevance to our build

- **Our pump and motor data is this domain.** The builder pack's `vibration_mm_s`, `bearing_temp_c`, `motor_current_a` and `speed_rpm` are the classic condition-monitoring signals. `BEARING_WEAR` is the most frequent historical case (8 of 50).
- **Copy the "Analysis and Diagnosis" reasoning:** symptom → likely cause → recommended check. For P-005: flow ↓ + current ↑, vibration flat → hydraulic restriction (fouling) rather than mechanical wear → inspect the hydraulic path.
- **Process impact.** Valmet frames monitoring by its effect on the process. The copilot can add one line on consequence: "reduced flow in Utility Island; P-005 is production-critical (A)".
- **Route-based monitoring = our avatar walk.** A technician walking a monitoring route past assets is exactly the scenario the demo simulates. Use that phrase in the pitch.
- **Sensor quality matters.** VS-002's `MOUNTING_ISSUE` and `DOC-VIBRATION_SENSOR-CORE` say poor sensor mounting should reduce confidence in nearby vibration-based diagnoses.
