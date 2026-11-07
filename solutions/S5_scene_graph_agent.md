# S5: 3D Scene Graph + Tool-Using Field-Service Agent ("The Plant That Explains Itself")

**One line:** Turn the extracted assets into a queryable 3D scene graph (structure → zones → objects → relations) joined to a knowledge graph built from all 16 Excel sheets, and let a Claude agent with spatial and data tools *run the mission*: pick the faulty device, plan the route, narrate nearby assets, and diagnose with citations.

**Bet:** 20% (AI grounding) + 15% (architecture) reward depth over polish. A scene graph is how robotics research (Hydra, ConceptGraphs) represents space, and an agent with real tools is easier to defend in Q&A than one big prompt.

---

## Architecture

```
            ┌──────── extraction (S1 or S3) ────────┐
PLY ───────▶│ structure planes, objects, OBBs, labels│──┐
            └────────────────────────────────────────┘  │
                                                         ▼
Excel (16 sheets) ──▶ knowledge graph ──▶  SCENE GRAPH (networkx / JSON-LD)
 Asset_Master, Current_State,               nodes: Area · Zone · Object · Asset · Doc · Event · WO · Case
 Telemetry, Alarms, Maintenance,            edges: near · above · on_floor · connected_pipe · mapped_to
 Service_Cases, Knowledge_Docs,                     · has_event · has_doc · same_class_case
 RAG_Corpus, Data_Quality
                                                         │
                     Claude agent (tool use) ◀───────────┘
                     tools: find_assets(filter) · plan_route(from,to,agent) · nearby(pos,r)
                            get_telemetry(asset,window) · detect_anomaly(asset) · search_docs(q)
                            get_history(asset) · data_quality(asset)
                                                         │
                     Rerun timeline: path, agent pose, highlighted boxes, agent "thoughts" log
```

## Pipeline

| Stage | What we do | Libraries |
|---|---|---|
| 1. Extraction | S1 (fast) or S3 (better) object boxes + labels. | — |
| 2. Spatial relations | Compute `near` (< 1.5 m), `above/below`, `on_floor`, `attached_to_wall`; group objects into zones by floor-space clustering. Pipe-like elongated objects that touch link equipment → `connected_pipe` edges (a crude P&ID). | numpy, scipy |
| 3. Knowledge graph | Load all sheets with pandas; nodes for assets, docs, events, work orders, cases; edges by `asset_id`, `knowledge_doc_id`, `asset_class`. | pandas, networkx |
| 4. Mapping | Hungarian assignment of Excel assets to scene objects (class + anchor distance). Graph edge `mapped_to` carries the mapping confidence. | scipy |
| 5. Analytics tools | Lightweight anomaly scoring on `Telemetry_Sample_3d` (rolling z-score / IsolationForest per asset) so the agent cites *evidence*, not only the pre-labelled `condition_state`. Respect `Data_Quality` flags (lower confidence, mention them). | pandas, scikit-learn |
| 6. Navigation | Occupancy grid + A* (as S1) wrapped as the `plan_route` tool; person and robot profiles. Optional: export a ROS `map.pgm/.yaml` (robotics sim bonus). | numpy |
| 7. Agent mission | Claude with tool use: (1) "find the device needing attention" → (2) `plan_route` → (3) step along the path calling `nearby` → short status narration per encountered asset → (4) on arrival: `get_telemetry`, `detect_anomaly`, `get_history`, `search_docs` → a diagnosis with citations, ranked next steps, and safety notes. Every claim must reference an ID; a server-side validator rejects unknown IDs. | anthropic SDK |
| 8. Viewer | **Rerun**: a timeline scrubber shows the whole mission (point cloud, boxes, path, agent pose, text log of agent reasoning). Easy to record and replay deterministically. | rerun-sdk |

## Build schedule

| When | Milestone |
|---|---|
| Fri night | Excel → knowledge graph; S1 extraction + Rerun scene |
| Sat 09:00 | Route tool + proximity; agent runs a scripted mission end-to-end |
| Sat 16:00 | Scene-graph relations, anomaly tool, citations validator |
| Sat night | Multiple scenarios (switch faulty device / person vs. robot), cached runs, video |
| Sun 08:00 | Slides with the graph diagram, README |

## Scoring estimate

| Criterion | Weight | Estimate | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Inherits S1/S3; relations add "awareness" value |
| Navigation + proximity | 25% | ●●●●○ | Grid + A*, narrated proximity |
| AI grounding | 20% | ●●●●● | Tool-using agent with evidence + validated citations |
| Backend architecture | 15% | ●●●●● | Graph + tools = clean, modular, robot-ready |
| Demo clarity | 10% | ●●●○○ | Rerun timeline is clear but technical-looking |

## Risks

- **Agent nondeterminism on stage:** record runs, and keep a Demo Mode that replays a cached tool trace.
- **Over-engineering the graph:** relations beyond `near` and `mapped_to` are a SHOULD.
- **Extraction still matters most (30%):** this plan still needs S1/S3 underneath.

## Hardware

Mac CPU + the Claude API.
