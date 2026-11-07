# S6: Rule Engine / Expert System ("Every Decision Is a Rule You Can Read")

**Type:** logic-based · **GPU:** no · **LLM:** optional (wording only) · **Runtime:** < 5 s end to end

**One line:** Geometry produces *facts*, a forward-chaining rule base turns facts into labels, relations, a chosen target and a diagnosis, and every output carries the chain of rules that produced it.

**Bet:** The Excel pack is built for rules. `Current_State` has `issue_code → recommended_next_check`, `Historical_Service_Cases` has `issue_code → interpretation → safe_evidence_workflow`, the knowledge docs say "prefer trend evidence", "reduce confidence on poor sensors", "never replace site procedures". A rule engine meets Builder Questions Q-03 (exact evidence IDs), Q-04 (prioritise) and Q-06 (lower confidence on poor quality) by construction, works offline, and never hallucinates on stage.

---

## How it works

```
geometry (S1 / S8)              Excel (pandas)
      │                               │
      ▼                               ▼
 facts: object(o7). height(o7,1.9). vertical_cylinder(o7). diameter(o7,0.6).
        near(o7,o12). on_floor(o7). asset(a17). class(a17,process_pump).
        health(a17,44). criticality(a17,a). issue(a17,fouling). dq_flag(a17,timestamp_jitter,high).
      │
      ▼
 rule layers (forward chaining, stratified)
   L1 classify   : label(O,tank)  :- vertical_cylinder(O), diameter(O,D), D > 0.8, on_floor(O).
                   label(O,pipe)  :- elongation(O,E), E > 6, diameter(O,D), D < 0.3.
                   label(O,valve) :- small(O), touches(O,P), label(P,pipe).
                   label(O,pump)  :- compact(O), on_floor(O), near(O,M), label(M,motor_like).
   L2 map        : compatible(O,A) :- label(O,pump), class(A,process_pump).  (+ Hungarian on top)
   L3 prioritise : priority(A, P) :- P = crit_w(A) * (100 - health(A)) * urgency_w(A) * conf(A).
                   target(A) :- argmax priority.
   L4 diagnose   : finding(A, F)  :- telemetry_trend(A, vibration, up), class(A, process_pump).
                   next_check(A, C) :- issue(A, I), service_case(_, I, C).
                   confidence(A, low) :- dq_flag(A, _, high).
                   safety(A) :- always  →  DOC-FIELD-SAFETY text.
      │
      ▼
 explanation trace: "P-005 chosen: criticality A (×3) · health 44 · urgency high (×2)
                     → priority 336 (rule L3.1, Current_State row ASSET-017)"
```

## Components

| Part | Choice | Notes |
|---|---|---|
| Rule engine | **Plain Python** rule functions with a decorator that logs `(rule_id, inputs, output)` | Fastest to build; zero dependencies. Alternatives: `clingo` (ASP, see S7) or `durable_rules` |
| Facts from geometry | S1 boxes + features: height, footprint, elongation, cylinder fit, touching neighbours | Each fact keeps a link back to its cluster ID |
| Telemetry facts | Rolling 6 h vs 72 h baseline per signal → `trend(A, signal, up/down/flat)`; threshold-free | pandas, ~50 ms for 4,320 rows |
| Target choice | Priority score from criticality × (100 − health) × urgency × confidence | With the current data this picks **P-005 (ASSET-017)**: criticality A, health 44, FOULING, urgency high |
| Diagnosis | Join `issue_code` → `Historical_Service_Cases` → `Knowledge_Docs` → `Maintenance_History` | Output = template text with filled-in IDs |
| LLM (optional) | Claude only rewrites the rule output into fluent prose, with a validator that the prose cites exactly the IDs in the trace | Demo works fully with the LLM off |
| Viewer | Viser / Rerun; a "Why?" button shows the rule trace | |

## What it needs

- People: 1 for geometry facts, 1 for rules + Excel, 1 for viewer (can be the same person as geometry).
- Libraries: numpy, scipy, pandas, openpyxl, viser. Python 3.12.
- Time: ≈ 10–14 h to a full demo.

## Scoring estimate

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Rules label better than raw clusters, but geometry is the ceiling |
| Navigation + proximity | 25% | ●●●●○ | Same grid + A* as S1 |
| AI grounding | 20% | ●●●●● | Every claim is traceable to a row ID; no hallucination possible |
| Backend architecture | 15% | ●●●●○ | Clear layers; rules are data, easy to extend |
| Demo clarity | 10% | ●●●○○ | The "Why?" trace is a strong Q&A moment |

## Risks

- Judges may see rules as "not AI". Answer: rules are the *grounding layer*; add the optional LLM narrator and a learned anomaly score (S11) on top.
- Hand-written shape rules are brittle on unseen geometry: keep a fallback label `unknown_object` rather than guessing (the DOC-3D-MAPPING doc literally says "never silently guess").
