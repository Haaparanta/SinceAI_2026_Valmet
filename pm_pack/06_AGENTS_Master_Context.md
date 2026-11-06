# AGENTS.md: Valmet "Point, Path, Why" Plant Twin

> [!WARNING]
> **PROVISIONAL: BASED ON MISSING DATA.**
> This architecture was designed from `README.md` only, **before** we received any partner data, API docs, NDA terms or evaluation criteria. The stack, file formats and contracts below are our `[HYPOTHESIS]`. They are **not** partner specifications. See "Final verification" at the bottom for what may change after the briefing.
>
> To use: `ln -s pm_pack/06_AGENTS_Master_Context.md AGENTS.md` (and the same for `CLAUDE.md` / `.cursorrules`).

---

## Mission

Turn a scanned industrial plant into a navigable, semantic digital world. Find **where** the equipment is, **what** it is, **how** people or robots move to it, **which** needs attention, and **why**, with cited explanations. `[README]`

Single-screen product: 1 question input → 1 central 3D view → 1 action card + 2 proof metrics.

---

## Provisional tech stack `[HYPOTHESIS]`

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vite + React + TypeScript + three.js (`@react-three/fiber`, `@react-three/drei`) | Fast to build; renders point clouds and boxes |
| Backend | Python 3.11 + FastAPI + Pydantic v2 | Same language as the 3D libraries |
| 3D processing | Open3D + NumPy (voxel downsample, RANSAC floor plane, DBSCAN clustering) | Mature and CPU-friendly |
| Navigation | 2D occupancy grid from floor-relative points + A* (person / robot clearance) | Simple and explainable |
| Semantic labeling | v0: geometric heuristics. v1: vision model on rendered views of each cluster. Optional: open-vocabulary 2D masks lifted to 3D if images are provided | Degrades gracefully with the data we get |
| LLM / RAG | Cloud LLM (Claude) via `LLMClient`; local open-weight fallback if the NDA requires it | Swappable in 1 file |
| Retrieval | Simple embedding index over docs linked by `asset_id` | Citations must reference real doc IDs |
| UI theme | **Cyberpunk v2**: shadcn/ui + Tailwind v4, tokens in `design/cyberpunk-tokens.css`, guide in `design/CYBERPUNK_THEME.md` | Decided by the team. Dark ("Night City") by default; status colors map to asset health |

---

## Folder tree

```
/
├── AGENTS.md -> pm_pack/06_AGENTS_Master_Context.md
├── README.md                  # challenge + <5-min setup (Gate 4)
├── pm_pack/                   # PM docs (this pack)
├── design/                    # Cyberpunk theme: tokens + guide (UI source of truth)
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes
│   │   ├── contracts.py       # Pydantic models (source of truth)
│   │   ├── config.py          # DATA_SOURCE, DEMO_MODE, LLM_PROVIDER
│   │   ├── data/
│   │   │   ├── base.py        # DataSource interface
│   │   │   ├── synthetic.py   # Branch B
│   │   │   └── partner.py     # Branch A  ← the ONLY file to edit when real data arrives
│   │   ├── pipeline/
│   │   │   ├── segment.py     # clustering → Asset[]
│   │   │   ├── classify.py    # semantic labels
│   │   │   └── navigate.py    # occupancy grid + A*
│   │   ├── assistant/
│   │   │   ├── llm_client.py  # cloud / local switch
│   │   │   ├── retrieve.py
│   │   │   └── ask.py         # orchestrates /ask, validates citations
│   │   └── demo_cache.py      # Demo Mode read/write
│   └── tests/
├── frontend/
│   └── src/
│       ├── contracts.ts       # mirrors backend/app/contracts.py
│       ├── App.tsx            # One-Screen layout
│       ├── Scene3D.tsx
│       ├── AskBar.tsx
│       ├── ActionCard.tsx
│       └── ProofMetrics.tsx
├── tools/
│   ├── gen_synthetic.py       # Branch B generator (≤ 15 min)
│   └── build_demo_cache.py
└── data/
    ├── synthetic/             # generated, committed (small)
    ├── partner/               # gitignored (NDA)
    └── cache/                 # Demo Mode JSON, committed
```

---

## Strict JSON contracts

`backend/app/contracts.py` is the **source of truth**. `frontend/src/contracts.ts` must mirror it exactly. Any change must update both files in the same commit.

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field

Vec3 = tuple[float, float, float]  # metres, scene coordinates, Z up

class BBox(BaseModel):
    center: Vec3
    size: Vec3

class Citation(BaseModel):
    doc_id: str
    snippet: str = Field(max_length=300)
    page: Optional[int] = None

class Asset(BaseModel):
    asset_id: str
    label: str                       # e.g. "Centrifugal pump"
    category: str                    # e.g. "pump" | "motor" | "tank" | "valve" | "other"
    confidence: float = Field(ge=0, le=1)
    bbox: BBox
    health: Literal["ok", "watch", "alert", "unknown"] = "unknown"
    source: Literal["detected", "registry", "synthetic"]
    doc_ids: list[str] = []

class Scene(BaseModel):
    scene_id: str
    units: Literal["m"] = "m"
    pointcloud_url: str              # downsampled file served to the viewer
    bounds: BBox
    entrance: Vec3
    assets: list[Asset]
    is_synthetic: bool

class Route(BaseModel):
    agent: Literal["person", "robot"]
    waypoints: list[Vec3]
    length_m: float
    est_time_s: float
    min_clearance_m: float

class AskRequest(BaseModel):
    scene_id: str
    question: str
    agent: Literal["person", "robot"] = "person"
    selected_asset_id: Optional[str] = None

class ProofMetrics(BaseModel):
    time_to_locate_s: float
    assets_labeled_pct: float
    assets_linked_pct: float

class AskResponse(BaseModel):
    answer: str                      # must be supported by citations
    focus_asset_ids: list[str]
    route: Optional[Route] = None
    citations: list[Citation]
    next_step: Optional[str] = None
    metrics: ProofMetrics
    from_cache: bool = False
```

```ts
// frontend/src/contracts.ts — mirror of contracts.py
export type Vec3 = [number, number, number];
export interface BBox { center: Vec3; size: Vec3 }
export interface Citation { doc_id: string; snippet: string; page?: number | null }
export type Health = "ok" | "watch" | "alert" | "unknown";
export interface Asset {
  asset_id: string; label: string; category: string; confidence: number;
  bbox: BBox; health: Health; source: "detected" | "registry" | "synthetic"; doc_ids: string[];
}
export interface Scene {
  scene_id: string; units: "m"; pointcloud_url: string; bounds: BBox;
  entrance: Vec3; assets: Asset[]; is_synthetic: boolean;
}
export interface Route {
  agent: "person" | "robot"; waypoints: Vec3[]; length_m: number; est_time_s: number; min_clearance_m: number;
}
export interface AskRequest { scene_id: string; question: string; agent?: "person" | "robot"; selected_asset_id?: string | null }
export interface ProofMetrics { time_to_locate_s: number; assets_labeled_pct: number; assets_linked_pct: number }
export interface AskResponse {
  answer: string; focus_asset_ids: string[]; route?: Route | null; citations: Citation[];
  next_step?: string | null; metrics: ProofMetrics; from_cache: boolean;
}
```

**API:** `GET /scene` → `Scene` · `POST /ask` (`AskRequest`) → `AskResponse` · `POST /route` → `Route` · `GET /health` → `{ok: true}`

---

## Branch A / Branch B data adapter rule

```python
# backend/app/data/base.py
class DataSource(Protocol):
    def load_scene(self) -> Scene: ...
    def load_documents(self) -> dict[str, str]: ...      # doc_id -> text
    def load_events(self) -> list[dict]: ...             # alarms / condition alerts
```

- `DATA_SOURCE=synthetic` → `SyntheticSource` reads `data/synthetic/` (Branch B).
- `DATA_SOURCE=partner` → `PartnerSource` reads `data/partner/` (Branch A).
- **Rule:** swapping synthetic for real partner data must require editing **only `backend/app/data/partner.py`**. Pipeline, assistant and frontend code must never branch on the data source. The only data-related flag the UI may read is `Scene.is_synthetic`, to show the "Synthetic data" badge.

---

## Deterministic Demo Mode contract

- `DEMO_MODE=1` (or the UI toggle) → `/ask` returns `data/cache/<sha1(scene_id + normalized_question + agent)>.json` with `from_cache: true`.
- The cache is built by `tools/build_demo_cache.py` for the **3 sample questions** shown as buttons in the UI.
- Demo Mode must work **with the network fully off**: no LLM or remote calls.
- On a cache miss in Demo Mode, return the nearest sample's cached response. Never error on stage.
- Regenerate the cache after any contract or pipeline change (Gate 4 checklist).

---

## Multi-agent division rules (Claude Code, Cursor, Codex, Antigravity)

1. **One owner per directory per sprint.** Write your agent's scope in the commit message, e.g. `[CV/claude-code] pipeline/navigate.py`.
   - `backend/app/pipeline/**`, `tools/gen_synthetic.py` → CV owner
   - `backend/app/assistant/**`, `demo_cache.py`, `tools/build_demo_cache.py` → AI owner
   - `frontend/**` → FE owner
   - `contracts.py` / `contracts.ts` → **PM approves changes**; both files change in the same commit
2. **Contracts first.** No agent invents new fields. Propose a contract change, get it approved, then implement it.
3. **Small commits to short-lived branches.** Rebase often. Never force-push `main`.
4. **No hallucinated data specs.** If an agent needs a fact about partner data, it checks `pm_pack/01_Partner_Briefing_Questions.md` for an answer. If it's unanswered, it writes `# GAP - ASK PARTNER:` in the code and uses the synthetic path.
5. **Every LLM answer is cited.** The server validates that each `doc_id` in `citations` exists in the retrieved set. Otherwise it returns "Insufficient documentation".
6. **Anti-scope:** no auth, no settings pages, no multi-page CRUD (see PRD WON'T).
7. **Theme:** all UI colors come from `design/cyberpunk-tokens.css`, with no hard-coded hex or OKLCH values. Equipment status uses `--status-ok/watch/alert/unknown` and always carries a text label. The route uses `--route` and the selected asset uses `--selection`. Follow the checklist in `design/CYBERPUNK_THEME.md` §11.
8. **Before handing off:** run `pytest backend/tests` and `npm run build` in `frontend/`.

---

## Final verification: top 5 `[GAP - ASK PARTNER]` items that could change this architecture

| # | Gap | What changes if the answer surprises us |
|---|---|---|
| 1 | **Capture format** (point cloud vs. mesh vs. 360° images vs. splats) | The viewer (`Scene3D.tsx`), `pointcloud_url` semantics, and whether 2D→3D lifting becomes the main labeling path |
| 2 | **Equipment data availability** (asset register, docs, alarms) | `load_documents` / `load_events` implementations. Whether `Asset.source = "registry"` replaces detection for IDs |
| 3 | **NDA / cloud restrictions** | `LLM_PROVIDER` defaults to local; the vision-model labeling path may need a local model; the public repo stays synthetic-only |
| 4 | **Primary user: technician vs. robot** | If robot: `Route` gains slope/step constraints, and the C1 sim export becomes a MUST |
| 5 | **Sunday winning criterion** | Technical jury: invest in segmentation accuracy and metrics. Business jury: invest in ROI and UX |
