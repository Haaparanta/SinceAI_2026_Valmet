# S7: Constraint Solving & Answer Set Programming ("Solve the Scene Like a Puzzle")

**Type:** logic-based · **GPU:** no · **LLM:** optional · **Runtime:** solver calls 0.1–5 s each

**One line:** State what a valid result looks like (labels, Excel mapping, mission) as declarative constraints, and let a solver (OR-Tools CP-SAT or clingo ASP) find the best consistent answer, instead of greedy heuristics.

**Bet:** Three parts of the brief are really combinatorial problems: which cluster is which kind of object, which Excel asset goes on which object, and which faulty device + route makes a meaningful mission. Solvers give globally consistent, explainable answers in seconds, and "we used a SAT solver to assign 30 assets to 170 objects under 9 constraints" is a crisp slide.

---

## Three solver problems

### 1. Consistent labelling (clingo ASP)

Every cluster gets exactly one label; physics and plant-layout rules must hold.

```prolog
1 { label(O,L) : class(L) } 1 :- object(O).
:- label(O,valve), not touches_pipe(O).               % valves sit on pipes
:- label(O,pump), not on_floor(O).                    % pumps stand on the floor
:- label(O,motor), not near_label(O,pump).            % motors drive pumps
:- label(O,tank), height(O,H), H < 80.                % tanks are tall (cm)
#maximize { S,O,L : label(O,L), score(O,L,S) }.       % geometry/VLM soft scores
```

Soft scores come from S1 shape features or S3 VLM confidence. The solver resolves conflicts *jointly* (a "pump" with no motor next to it gets re-labelled), which greedy per-cluster rules can't do.

### 2. Excel → scene mapping (OR-Tools CP-SAT)

| Constraint | Kind |
|---|---|
| Each of the 30 Excel assets maps to at most one object; each object to at most one asset | hard |
| `asset_class` must be compatible with the object label | hard |
| Assets in the same `area_id` should be spatially clustered (area = a floor zone) | soft |
| Motor `M-00x` should sit next to pump `P-00x` | soft |
| The target device must be reachable (free-space path exists) | hard |
| Maximise mapped objects × mapping confidence | objective |

30 × ~170 boolean variables: CP-SAT solves this in **well under a second**.

### 3. Mission design (CP-SAT or ASP)

Choose the faulty target and the route waypoints so the walk is a good demo *and* logical:

- the target = the highest-priority non-healthy asset (criticality × health × urgency) that is reachable;
- the path passes ≥ N healthy mapped assets (so proximity display has content);
- a route-length cap, no backtracking.

A* still computes the actual collision-free segments; the solver only chooses the order of waypoints (a small orienteering/TSP problem).

## Components

| Part | Choice |
|---|---|
| Solvers | `ortools` (CP-SAT), `clingo` (ASP). Both install on **Python 3.12** (`ortools` has no 3.15 wheel) |
| Facts | S1 or S8 geometry features, S3 VLM scores if available |
| Explanations | ASP: print the satisfied rules for each chosen atom; CP-SAT: report which constraints are tight |
| Everything else | S1 grid + A*, Viser, Claude for prose |

## What it needs

- 1 person comfortable with declarative modelling (ASP or MiniZinc-style thinking); others as S1.
- Time: ≈ 4–6 h for the three models on top of the S1 baseline.

## Scoring estimate

| Criterion | Weight | Est. | Why |
|---|---|---|---|
| Extraction density | 30% | ●●●○○ | Better *consistency* of labels, not more boxes |
| Navigation + proximity | 25% | ●●●●○ | A* + optimised mission ordering |
| AI grounding | 20% | ●●●●○ | Decisions are provably consistent with stated constraints |
| Backend architecture | 15% | ●●●●● | Declarative, modular, very defensible |
| Demo clarity | 10% | ●●●○○ | Needs a good slide to show why it matters |

## Risks

- Learning curve if nobody on the team has used ASP: start with CP-SAT for mapping only (easiest win), add ASP labelling if time allows.
- Over-constraining → UNSAT. Keep everything soft except one-to-one and class compatibility; log which constraint failed.
