# Turning data into better valve performance with digital services

| | |
|---|---|
| URL | https://www.valmet.com/insights/blogs/flow-control/2026/turning-data-into-better-valve-performance-with-digital-services/ |
| Page title | "Turning data into better valve performance with digital services" |
| Publisher / date | Valmet Flow Control blog · **19 March 2026** |
| Interviewee | Boris Volavicius, Head of Digitalization Sales, Flow Control business area (the intro calls him "Digitalization Sales Director") |
| Pack's design implication | Fleet-level analysis, diagnostic categories and maintenance prioritization |
| Read | 2026-11-06, body text read directly |

## Page structure

An interview in Q&A form:

1. What is the digitalization offering designed for?
2. What are our digital services for flow control?
3. How it works, end-to-end
4. Prioritization vs. fixed criticality classes
5. What kind of data can we get from digital valve controllers?
6. How do customers benefit from digital solutions?
7. Summary of the content
8. What is ValvesNow?
9. How can we help you? / related cards

## Section by section

### Intro

Customers are building their own digital strategies and expect suppliers' digital services to help them run better. Access to data is presented as the route to operational efficiency.

### 1. What is the offering designed for?

Raising efficiency and reliability with analytics and connectivity: tools to monitor valve performance, support optimal operation and extend the life of critical equipment. Two pain points are named:

- **limited visibility** into valve condition
- an **incomplete picture of the installed base**

Smart-positioner diagnostics are presented in a prioritised, readable form. Customers also get installed-base documentation, the right spare-part sets and, in future, online spare-parts purchasing. Valmet invites customers to describe their gaps so views, reports and scope (inventory, purchasing, extra KPIs) can be tailored.

### 2. What are the digital services?

**Valve Performance Monitoring (VPM)** is the main service. It turns diagnostics into expert recommendations that raise availability, reliability and performance. **ValvesNow** (cloud) produces the automatic diagnostics: collects valve data, runs **AI-assisted fleet-level analysis**, highlights worst performers and prioritises issues. Dashboards, reports and expert collaboration live in the **Valmet Customer Portal**, giving one actionable view of the installed base.

### 3. How it works, end to end

```
site connected
   → ValvesNow collects diagnostics from Neles controllers   (daily)
   → comprehensive fleet analysis                              (weekly)
   → findings sorted into categories, presented as a prioritised list
   → VPM experts add monitoring, periodic diagnostic reports, recommended actions
   → everything delivered in the customer's Customer Portal workspace
```

### 4. Prioritisation vs fixed criticality classes

- **Default:** ValvesNow's algorithmic score and categories, **combined with a local valve-service expert's assessment**.
- **Optional:** a formal criticality classification (**high / medium / low**) added per scope.
- Uses: predictive maintenance, **shutdown scope optimisation**, spare-parts strategy.
- The ValvesNow dashboard shows prioritised issues and trends; the Portal centralises status, documents, reports and collaboration.

### 5. What data comes from digital valve controllers?

Neles **NDX** and **ND9000** controllers gather extensive diagnostics. Findings are analysed in **five categories**:

| # | Category | Example signals |
|---|---|---|
| 1 | Control performance | setpoint tracking, position deviation |
| 2 | Mechanical issues | friction, stiction, actuator load |
| 3 | Operation style | how the valve is driven (e.g. constant hunting, near-closed operation) |
| 4 | Working environment | supply pressure, temperature |
| 5 | Device alarms | controller self-diagnostics |

*(Example signals are our interpretation; the article only names the categories.)*

Valves are ranked so the worst rise to the top, and teams can filter by category, process area and more.

### 6. Customer benefits

Better operational efficiency, less downtime, optimised maintenance schedules, longer asset life, simpler purchasing, and closer day-to-day collaboration with the local flow-control service team.

### 7–9. Summary, ValvesNow, related cards

Repeat the points above. Related cards: the Mercer Stendal VPM story (500 critical valves, 24/7 monitoring, four expert reports a year, five years), "Cloud based diagnostics for valves" (2025), "What is AI in valve diagnostics and digital services?" (2025: AI learns from past events and improves with input, paired with service expertise), and "50 years of flow control services" (**40+ service centres, 400+ service professionals**).

## Key facts

| Fact | Value |
|---|---|
| Diagnostic sources | Neles NDX, Neles ND9000 |
| Cadence | daily collection, weekly fleet analysis |
| Categories | 5 (control performance, mechanical, operation style, working environment, device alarms) |
| Prioritisation | algorithm score + local expert; optional high/medium/low criticality |
| Delivery | Valmet Customer Portal |
| Scale of service org | 50 years, 40+ centres, 400+ professionals |

## Relevance to our build

- **Use the five categories as the copilot's fault taxonomy for valves.** Mapping to the builder pack:

  | Pack issue code | Category |
  |---|---|
  | `POSITION_DEVIATION` | control performance |
  | `STICTION_TREND`, `ACTUATOR_FRICTION`, `SEAT_LEAKAGE_SUSPECTED` | mechanical issues |
  | `SUPPLY_PRESSURE_LOW` | working environment |
  | `CALIBRATION_DRIFT` | device alarms |

- **Algorithm + human.** Valmet's own default is "score, then a human expert confirms". Our copilot should present a ranked hypothesis and a recommended check, and leave the decision to the technician. This lines up with `DOC-FIELD-SAFETY`.
- **Criticality tiers.** The optional high/medium/low maps directly to `Asset_Master.criticality` (A/B/C). Sort and colour by it.
- **Shutdown scope.** A nice extra copilot output: "include CV-003 and CV-009 in the next shutdown scope".
