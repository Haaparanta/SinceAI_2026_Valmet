# S4: Photoreal Web Twin with NavMesh ("Game-Engine Navigation in the Browser")

**One line:** A Python backend precomputes assets and a voxelised collision mesh; a three.js front end renders the *real* Gaussian splat, builds a Recast NavMesh, and runs a humanoid/robot agent with crowd steering, proximity frames and an AI copilot panel.

**Bet:** 25% (navigation) + 10% (demo clarity) = 35% of the score is about how convincing the walk looks. A photoreal splat with a game-grade navmesh and a smooth walking avatar is the most memorable demo in the room.

---

## Architecture

```
Python backend (offline)                     Browser (three.js, Vite + TS)
──────────────────────────                   ────────────────────────────────
clean.py   → scene_clean.ply / .spz  ───────▶ Spark / gaussian-splats-3d renderer
extract.py → assets.json (S1 or S3 boxes) ──▶ box frames + labels (instanced lines)
collide.py → occupancy voxels → collision.glb ▶ recast-navigation-js: NavMesh + Crowd agent
map.py     → excel_mapping.json ────────────▶ proximity panel (KD-tree in JS)
FastAPI /diagnose (Claude, cited) ◀──────────  arrival trigger
```

## Pipeline

| Stage | What we do | Libraries |
|---|---|---|
| 1. Clean + compress | Filter as in S1; export the clean splat as `.splat`/`.spz` (≈ 20–40 MB) for the web. | numpy, plyfile |
| 2. Asset extraction | Re-use S1 (fast) or S3 (better) to produce `assets.json` with OBBs + labels. | — |
| 3. Collision geometry | Voxelise occupied space (5 cm), marching cubes → a simplified mesh `collision.glb`. Floor = a plane + the detected floor voxels. | scikit-image `marching_cubes`, trimesh |
| 4. NavMesh | In the browser (or offline): Recast builds a navmesh with agent radius / height / max climb / max slope. Robot and person profiles = two navmeshes. | `recast-navigation` (WASM) |
| 5. Agent | Detour Crowd moves a rigged avatar (Mixamo-style walk cycle, or a simple wheeled robot model) along the path at walking speed; the camera follows with a third-person rig. | three.js, recast-navigation |
| 6. Proximity | Every frame: assets within R → frames glow in the status colour (`--status-ok/watch/alert`), floating labels with tag, class, health score, latest telemetry. | three.js CSS2DRenderer |
| 7. Excel mapping | Same Hungarian mapping, exported as JSON. | Python |
| 8. AI copilot | On arrival: the FastAPI `/diagnose` endpoint calls Claude with the target's Excel context (state, telemetry trend, alarms, work orders, service cases, docs); the answer streams into a cyberpunk-themed side panel with clickable citations. Demo Mode = cached JSON. | FastAPI, anthropic SDK |
| 9. UI | Reuses the repo's Cyberpunk v2 tokens (`design/cyberpunk-tokens.css`). | Tailwind / plain CSS |

## Build schedule

| When | Milestone |
|---|---|
| Fri night | Clean splat renders in the browser; Python S1 extraction starts in parallel |
| Sat 09:00 | Collision mesh + navmesh + agent walking to a hard-coded target |
| Sat 16:00 | Assets + Excel mapping + proximity frames + `/diagnose` |
| Sat night | Avatar animation, camera choreography, Demo Mode cache, video |
| Sun 08:00 | Slides/README |

## Scoring estimate

| Criterion | Weight | Estimate | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Inherits S1/S3; not the focus |
| Navigation + proximity | 25% | ●●●●● | Real navmesh, a smooth agent, visible proximity reactions |
| AI grounding | 20% | ●●●●○ | Same Claude flow, better presentation |
| Backend architecture | 15% | ●●●○○ | Split front/back; more glue |
| Demo clarity | 10% | ●●●●● | Photoreal, cinematic |

## Risks

- **Front-end time sink** (the brief explicitly prefers backend over UI polish). Cap UI work; reuse library examples.
- **Splat + many CSS labels** can drop FPS: cap visible labels to the nearest 12.
- **Navmesh from a noisy voxel mesh** may have holes: close holes in the occupancy grid before marching cubes.
- **Two codebases** (Python + TS) need a strict JSON contract.

## Hardware

Mac CPU for the backend; any modern browser with WebGL2.
