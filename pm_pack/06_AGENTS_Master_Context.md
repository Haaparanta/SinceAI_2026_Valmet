`// VALMET × SINCE AI 2026 · PM PACK · 06`

# 06 — AGENTS Master Context

Ready-to-symlink `AGENTS.md` (also works as `CLAUDE.md` / `.cursorrules`): the stack, the folder tree, the frozen JSON contracts, the scan recipe, the copilot contract and the rules for four coding agents working on one repo.

`v1.0.0 · GENERATED 2026-11-06 20:45 EET · SOURCE: BRIEF.DOCX + BUILDER PACK v4.0 + BOILER ROOM.PLY · WEDGE: D (LOCKED) · STATUS: BUILD`

> [!NOTE]
> **Evidence tags.** `[SOURCE DATA]` = stated in the challenge brief, the builder-pack xlsx, or measured on the `.ply`. `[GAP - ASK PARTNER]` = not in the source data; the question lives in `01_Partner_Briefing_Questions.md`. `[HYPOTHESIS]` = our deduction or design choice. Team roles are slots (**PM / CV / AI / FE**) because the team composition was not given; map them to names on Friday night.

> [!TIP]
> Symlink from the repo root: `ln -s pm_pack/06_AGENTS_Master_Context.md AGENTS.md && ln -s AGENTS.md CLAUDE.md && ln -s AGENTS.md .cursorrules`. Every agent reads this file first, then `data/scene_graph.json`, then `pm_pack/05_Execution_Roadmap_and_Milestones.md` for the current sprint.

---

## 0. Project in one screen

**Approve-to-Build Twin (`a2b`)** — an offline Python pipeline turns `Industrial Boiler Room (1).ply` (3D Gaussian Splatting) into a queue of object proposals; a web curator shows them **one by one** and a human approves each into the central scene graph, which **photographs itself after every addition (new object red, rest translucent grey)**; the finished twin is a **three.js** web app where a service avatar auto-walks a collision-free route to the faulty pump and a grounded copilot explains why, and the same scene opens in **WebXR on a Meta Quest 3**.

**Five non-negotiables** `[SOURCE DATA — user]`: (1) objects identified one by one, added only on user approval; (2) web interface for approval; (3) model work runs offline (batch pipeline; browser only reviews and renders); (4) a snapshot after every addition — new object red, everything else see-through grey; (5) final demo in the web with three.js, walkable, Quest 3 compatible (stretch).

**Judging weights** `[SOURCE DATA — brief §06]`: extraction density & 3D framing 30 % · obstacle-aware navigation & proximity display 25 % · AI diagnostics, grounding & explainability 20 % · backend architecture 15 % · demo clarity & innovation 10 %. UI polish is explicitly not rewarded.

**Deadline** `[SOURCE DATA — README]`: Sun 2026-11-08 10:00 EET. Internal: code freeze 08:00, submit 09:15.

**Done looks like** (`02 §3` MUST `M1`–`M12`): `scene_graph.json` with ≥ 60 human-approved objects and all 30 xlsx assets bound; one PNG per approval in `data/snapshots/`; `route.json` for `P-005`, `M-006`, `P-002` with zero blocked cells; the twin runs with Wi-Fi off in Demo Mode; a `Diagnosis` for each target whose every `evidence_id` exists; video ≤ 5 min, 5–8 slides, README, technical note `[SOURCE DATA — brief §07]`.

**Sample targets** `[SOURCE DATA — Current_State]`: `ASSET-017 · P-005 · PROCESS_PUMP · FOULING · health 44 · urgency high` (default), `ASSET-024 · M-006 · ELECTRIC_MOTOR · OVERHEATING · health 45`, `ASSET-014 · P-002 · PROCESS_PUMP · CAVITATION_RISK · health 45`.

---

## 1. Tech stack (provisional) `[HYPOTHESIS]`

| Layer | Choice | Why |
|---|---|---|
| Python | **3.12 via `uv`** (not the Homebrew 3.15 — no numpy/open3d wheels for it yet) | reproducible venv, fast installs |
| Geometry | `numpy`, `scipy` (cKDTree, RANSAC helpers), `scikit-learn` (DBSCAN), `open3d` *optional* (alpha shapes, hulls for `S2`) | CPU-only; no GPU confirmed `[GAP - ASK PARTNER — G6]` |
| Data | `openpyxl` (xlsx → JSON), `pydantic>=2` (contracts), `orjson` | pack has no formulas, plain values |
| API | `fastapi`, `uvicorn[standard]`, `python-multipart` (snapshot upload) | thin, typed, auto-docs at `/docs` |
| LLM | official `anthropic` SDK, default model **`claude-opus-5-5`**; `LLMClient` interface with an **Ollama** backend for offline runs | structured output + citation validator; the user may switch to `claude-haiku-5-5` / `claude-sonnet-5-5` for speed |
| Web | Node ≥ 20, **Vite + TypeScript + three.js** (`three` latest stable), optional splat renderer *e.g.* `@mkkellogg/gaussian-splats-3d` for `S4`, three's `VRButton`/WebXR for `S3` | the brief lists "Three.js/Web" among accepted visualizers `[SOURCE DATA — brief §04]` |
| Video | `ffmpeg` via Homebrew (`S7` timelapse, final cut) | not installed on this Mac yet |
| Rust (optional) | `cargo` is present; `C4` only after Gate 3 | brief invites Python **or** Rust |

### Bootstrap

> [!NOTE]
> **As built (2026-11-07).** `make setup` does all of this: `uv sync` from `pyproject.toml`/`uv.lock`, `npm install` in `web/`, and the `data/raw` symlink. `make help` lists the targets. ffmpeg is not needed: `make timelapse` uses the `imageio-ffmpeg` wheel. open3d is not installed (its wheel needs Homebrew `libusb`), and scipy covers the hulls. The block below is the original plan.

```bash
# from the repo root
uv python install 3.12
uv venv --python 3.12 && source .venv/bin/activate
uv pip install numpy scipy scikit-learn openpyxl "pydantic>=2" orjson fastapi "uvicorn[standard]" python-multipart anthropic
uv pip install open3d || true                     # optional; skip if the wheel is missing
ln -s ../Source-Data-Do-Not_change data/raw       # raw data is read-only, .ply/.mp4 are gitignored
export ANTHROPIC_API_KEY=...                      # or `ant auth login`; never commit keys
uv run python pipeline/01_clean.py                # → data/derived/clean.npz, scene_points.bin
uv run python pipeline/05_bind_metadata.py --dump # → data/derived/xlsx/*.json
uv run uvicorn api.main:app --reload --port 8000
cd web && npm ci && npm run dev                   # http://localhost:5173  (/curate and /)
brew install ffmpeg                               # S7 + video, background
```

`make check` = `uv run ruff check . && uv run pytest -q && (cd web && npm run typecheck && npm run build)`. `make demo` = pipeline (cached) + API + web in Demo Mode.
While developing, run only some tests: `make test T="parts cleaning"` (files), `make test K=lamp` (test-name match), `make test-pick` (menu), `make test-changed` (tests related to changed .py files), `make test-failed` (last failures); `make test-list` shows what can be picked. `make check` always runs every test.
Frontend: `make test-web` drives `index.html` and `capture.html` in headless Chromium (`tests/web/*.test.mjs`, `node:test` + `playwright-core`); with no `.ply` it first writes a synthetic viewer scene (`make viewer-fixture`). It is not part of `make check`.

---

## 2. Folder tree

> [!NOTE]
> **As built (2026-11-07).** This tree is the target. The repo today has `pipeline/{01_clean,05_bind_metadata,build}.py` + `pipeline/stepbuild/` (step-by-step build), `build/` (build state), `images/` (one numbered image per step), `api/main.py` only, `web/src/{main,scene,capture}.ts` (viewer + snapshot page), and `scripts/{check_contracts,export_viewer_scene,timelapse,run_tests}.py`. `data/scene_graph.json`, `02–04`, `06–07`, `api/routers/` and the curator/twin/xr folders do not exist yet. The live map is the [README](../README.md#repo-map).

```
a2b/
├── AGENTS.md -> pm_pack/06_AGENTS_Master_Context.md
├── Makefile
├── pipeline/                 # OFFLINE. Owner: Claude Code. Each step is idempotent and writes to data/derived/
│   ├── 01_clean.py           # PLY → clean.npz + scene_points.bin (M1)
│   ├── 02_floor_grid.py      # floor plane, occupancy grid, walkable.png (M2)
│   ├── 03_propose.py         # clustering → OBBs → proposals.json (M3)
│   ├── 04_mesh.py            # per-object hull/alpha-shape .glb (S2)
│   ├── 05_bind_metadata.py   # xlsx → JSON, AssetRecord merge, Scene_Anchors rewrite (M6)
│   ├── 06_route.py           # A* with clearance → route.json (M7)
│   ├── 07_demo_cache.py      # cached Diagnosis JSON for the 3 targets (M11)
│   └── common/               # ply_io.py, geometry.py, xlsx_io.py, ids.py
├── api/                      # Owner: Claude Code
│   ├── main.py               # FastAPI app, CORS for localhost:5173, static /data
│   ├── routers/              # proposals.py scene.py assets.py copilot.py snapshots.py workorders.py
│   ├── services/             # scene_graph.py (locking + atomic write), retrieval.py, validator.py
│   └── llm_client.py         # LLMClient protocol; AnthropicClient, OllamaClient, CachedClient
├── web/                      # Owner: Cursor. Vite + TS + three.js
│   └── src/
│       ├── curator/          # Screen A: proposal view, keyboard, approve flow, snapshot capture
│       ├── twin/             # Screen B: twin scene, avatar, proximity ring, diagnosis card, status bar
│       ├── xr/               # VRButton, controller locomotion, snap turn (S3)
│       ├── scene/            # points loader, OBB meshes, status materials, route line, grid collision
│       └── api/              # typed fetch wrappers generated from contracts/ts
├── contracts/                # SHARED. Changed only with a note in docs/CONTRACT_CHANGES.md
│   ├── py/a2b_contracts/     # pydantic v2 models (this file §4)
│   ├── ts/                   # identical TypeScript types
│   └── json-schema/          # exported from pydantic; CI diff against ts
├── data/
│   ├── raw -> ../Source-Data-Do-Not_change   # symlink, read-only
│   ├── derived/              # clean.npz scene_points.bin grid.npz walkable.png proposals.json meshes/ xlsx/ route_*.json
│   ├── scene_graph.json      # THE central scene (append-only objects list)
│   ├── snapshots/            # 0001_obj-0001_P-005.png …
│   └── cache/                # diagnosis_ASSET-017.json … (Demo Mode)
├── tests/                    # Owner: Codex. pytest (pipeline, validator, routes) + vitest (grid collision)
├── scripts/                  # Owner: Codex. timelapse.sh, check_counts.py, verify_cache.py
├── docs/                     # Owner: Antigravity. slides/, video_script.md, technical_note.md, CONTRACT_CHANGES.md
└── pm_pack/                  # this pack
```

---

## 3. The scan: measured facts and reading recipe `[SOURCE DATA — measured 2026-11-06]`

> [!NOTE]
> **As built (2026-11-07).** Since 2026-11-06 23:15 the master scan is **`data/raw/Equipment Room.ply`**: 1,676,481 splats, same 59-float layout, every row real (no random tail). `pipeline/01_clean.py` and `pipeline/build.py` read it by default; it is rotated 180° about z into the world frame (`common/orientation.py`, frame `world-rotz180-v1`). The facts below are for the original boiler-room file. In that file only rows 0–502,481 are real, and the rest are random bits (see [analysis/ply_study](../analysis/ply_study/README.md)).

- File: `data/raw/Industrial Boiler Room (1).ply`, 355 MB, binary little-endian PLY, header 1 503 bytes, `comment Generated by EGS`.
- `element vertex 1506136`, 59 × float32 per record (236 bytes): `x y z`, `scale_0..2` (log-scale), `rot_1 rot_2 rot_3 rot_0` (**quaternion in that header order**), `f_dc_0..2`, `opacity` (logit), `f_rest_0..44` (SH degree 3).
- Only ~500 k (33 %) are usable: 56 % lie beyond ±100 units, 0.8 % are NaN, 10 % are near-transparent, and ~20 % of the remainder collapse at the origin.
- Clean room (p1–p99): `x −4.7 … 3.9`, `y −1.5 … 1.1`, `z −4.4 … 0.0` → ≈ **8.6 × 4.4 × 2.6 units, y-up, floor ≈ y −0.9**. Metric scale is **unverified** `[GAP - ASK PARTNER — G1]`: report "scene units (u)" until answered.
- Colour: `rgb = clip(0.5 + 0.28209479 · f_dc, 0, 1)`.

```python
# pipeline/common/ply_io.py
import numpy as np

SH_C0 = 0.28209479

def read_header(path: str) -> tuple[int, int, list[str]]:
    with open(path, "rb") as f:
        header = b""
        while not header.endswith(b"end_header\n"):
            header += f.readline()
    lines = header.decode().splitlines()
    n = int(next(l for l in lines if l.startswith("element vertex")).split()[-1])
    names = [l.split()[-1] for l in lines if l.startswith("property")]
    return n, len(header), names

def load_gaussians(path: str) -> np.ndarray:
    n, offset, names = read_header(path)
    dt = np.dtype([(name, "<f4") for name in names])          # 59 fields, 236 bytes
    return np.fromfile(path, dtype=dt, count=n, offset=offset)  # ~2 s

def clean_mask(g: np.ndarray, room_limit: float = 20.0, min_opacity: float = 0.05,
               max_scale: float = 2.0) -> np.ndarray:         # thresholds [HYPOTHESIS]
    xyz = np.stack([g["x"], g["y"], g["z"]], 1)
    finite = np.isfinite(xyz).all(1)
    in_room = (np.abs(xyz) < room_limit).all(1)
    not_origin = (np.abs(xyz) > 1e-3).any(1)
    opacity = 1.0 / (1.0 + np.exp(-np.clip(g["opacity"], -30, 30)))
    scale = np.exp(np.clip(np.stack([g["scale_0"], g["scale_1"], g["scale_2"]], 1), -30, 30))
    return finite & in_room & not_origin & (opacity >= min_opacity) & (scale.max(1) < max_scale)

def rgb_from_dc(g: np.ndarray) -> np.ndarray:
    dc = np.stack([g["f_dc_0"], g["f_dc_1"], g["f_dc_2"]], 1)
    return np.clip(0.5 + SH_C0 * dc, 0.0, 1.0)
```

`scene_points.bin` layout (for the browser): `uint32 count`, then `count × float32[3]` xyz, then `count × uint8[3]` rgb. Voxel-downsample to ≤ 400 k points before writing; ≤ 300 k for the Quest build.

**Status mapping** `[HYPOTHESIS]` (from `Current_State.condition_state`): `healthy → OK` (green) · `watch → WATCH` (yellow) · `degraded → WATCH`, label `DEGRADED` (yellow) · `attention_required → ALERT` (red) · unbound context object → `UNKNOWN` (grey). Status is never colour-only: every chip carries the text. Colours come from `design/cyberpunk-tokens.css` (`--status-ok/watch/alert/unknown`, `--route`, `--selection`).

**Snapshot recipe** (`M5`): fixed isometric camera (`position = bounds_center + (6, 7, 6) u`, look at `bounds_center`, `fov 35`); `WebGLRenderer({ preserveDrawingBuffer: true, antialias: true })` on an offscreen 1280 × 800 canvas; materials: the newly approved object `MeshBasicMaterial({ color: 0xff2d55 })` opaque, every other approved object `MeshBasicMaterial({ color: 0x9aa0a6, transparent: true, opacity: 0.25, depthWrite: false })`, raw points hidden, floor outline at 10 % opacity; `renderer.render()` then `canvas.toDataURL("image/png")` → `POST /api/snapshots` → server writes `data/snapshots/{seq:04d}_{object_id}[_{tag}].png` and sets `snapshot_uri` on the object. Curator shows the thumbnail strip from the same files.

**Walkable grid** (`M2`, `M7`, `M10`): `grid.npz` holds `origin_xz`, `resolution = 0.05`, `floor_y`, `occupied[ny, nx]` (bool) built from points with `floor_y + 0.10 ≤ y ≤ floor_y + 1.90`, and `blocked_human` / `blocked_robot` = `occupied` dilated by 0.30 u / 0.35 u `[HYPOTHESIS]`. The same file is served to the browser; walk mode and the avatar collide against `blocked_human`, the robot against `blocked_robot`.

---

## 4. Contracts (frozen; identical names in Python and TypeScript)

### 4.1 Pydantic v2 — `contracts/py/a2b_contracts/models.py`

```python
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]  # x, y, z, w — three.js order

ClassGuess = Literal[
    "CONTROL_VALVE", "PROCESS_PUMP", "ELECTRIC_MOTOR", "PRESSURE_TRANSMITTER", "VIBRATION_SENSOR",
    "pipe", "tank", "boiler", "cabinet", "structure", "other",
]
Status = Literal["OK", "WATCH", "ALERT", "UNKNOWN"]
ConditionState = Literal["healthy", "watch", "degraded", "attention_required"]  # [SOURCE DATA]

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # emits additionalProperties: false in JSON Schema

class OBB(Strict):
    center: Vec3
    size: Vec3            # full extents along the local axes, scene units
    rotation: Quat

class Proposal(Strict):
    proposal_id: str                  # "prop-0042"
    rank: int
    obb: OBB
    point_count: int
    point_indices_uri: str            # data/derived/proposals/prop-0042.npy (uint32 indices into clean.npz)
    label_guess: str
    class_guess: ClassGuess
    confidence_auto: float = Field(ge=0, le=1)
    status: Literal["pending", "approved", "rejected", "skipped"] = "pending"

class ApprovedObject(Strict):
    object_id: str                    # "obj-0042"
    source_proposal_id: str
    label: str
    class_guess: ClassGuess
    confidence_auto: float
    obb: OBB
    mesh_uri: Optional[str] = None    # data/derived/meshes/obj-0042.glb (S2)
    point_indices_uri: str
    asset_id: Optional[str] = None    # "ASSET-017" or None → context object
    tag: Optional[str] = None         # "P-005"
    mapping_confidence: float         # 1.0 when a human approved the binding
    mapping_method: Literal["human_approved", "procedural", "none"]
    approved_by: str
    approved_at: datetime
    snapshot_uri: Optional[str] = None

class SceneInfo(Strict):
    source_file: str
    units: Literal["scene_units", "metres"] = "scene_units"   # metres only after G1 is answered
    up_axis: Literal["y"] = "y"
    bounds_min: Vec3
    bounds_max: Vec3
    floor_y: float
    grid_resolution: float = 0.05
    is_synthetic_metadata: bool = True

class SceneCounts(Strict):
    proposals: int
    approved: int
    rejected: int
    skipped: int
    bound: int            # approved objects with an asset_id

class SceneGraph(Strict):
    version: str
    scene: SceneInfo
    objects: list[ApprovedObject]     # append-only
    target_object_id: Optional[str] = None
    counts: SceneCounts

class CurrentState(Strict):            # columns of Current_State [SOURCE DATA]
    health_score: float
    condition_state: ConditionState
    issue_code: str
    issue_summary: str
    urgency: str
    recommended_next_check: str
    model_confidence: float
    last_updated: datetime
    knowledge_doc_id: str

class TelemetryRow(Strict):            # class-specific columns are optional [SOURCE DATA]
    timestamp: datetime
    process_pressure_bar: Optional[float] = None
    process_flow_pct: Optional[float] = None
    position_setpoint_pct: Optional[float] = None
    position_actual_pct: Optional[float] = None
    pneumatic_supply_bar: Optional[float] = None
    stiction_index: Optional[float] = None
    load_for_opening_pct: Optional[float] = None
    vibration_mm_s: Optional[float] = None
    bearing_temp_c: Optional[float] = None
    motor_current_a: Optional[float] = None
    speed_rpm: Optional[float] = None
    sensor_bias: Optional[float] = None
    signal_quality_pct: Optional[float] = None

class EventRow(Strict):
    event_id: str; timestamp: datetime; event_type: str; severity: str; event_code: str
    description: str; source: str; status: str

class WorkOrderRow(Strict):
    work_order_id: str; opened_at: datetime; action: str; maintenance_type: str; priority: str
    result: str; duration_h: float; downtime_h: float; role: str; knowledge_doc_id: str

class DocRef(Strict):
    doc_id: str; title: str; scope: str; document_role: str; content: Optional[str] = None

class DataQualityRow(Strict):
    issue_id: str; issue_type: str; severity: str; source_sheet: str; recommended_handling: str

class AssetRecord(Strict):             # Asset_Master + Current_State + windows [SOURCE DATA]
    asset_id: str; tag: str; asset_class: str; area_id: str; area_name: str; process_context: str
    criticality: str; installation_date: datetime; last_service_date: datetime
    service_interval_days: int; connectivity_profile: str
    current_state: CurrentState
    status: Status
    telemetry_window: list[TelemetryRow]      # the 3-day sample for this asset
    events: list[EventRow]
    maintenance_history: list[WorkOrderRow]
    documents: list[DocRef]
    data_quality: list[DataQualityRow]
    object_id: Optional[str] = None           # set once bound in the curator
    anchor: Optional[OBB] = None              # real position after binding

class Route(Strict):
    target_asset_id: str
    target_object_id: str
    start: Vec3
    waypoints: list[Vec3]                     # on the floor plane, smoothed
    length: float
    min_clearance: float
    grid_resolution: float
    agent_radius: float
    planner: Literal["astar", "manual_verified"]
    computed_at: datetime

class CopilotQuery(Strict):
    asset_id: str
    question: Optional[str] = None
    mode: Literal["arrival", "along_route"] = "arrival"
    demo_mode: Optional[bool] = None          # None → server setting

class Evidence(Strict):
    evidence_id: str          # EVT-00123 | WO-00045 | DOC-PROCESS_PUMP-CORE | CASE-003 | DQ-0007
                              # | CS:ASSET-017 | TLM:ASSET-017:2026-10-05T00:00/2026-10-07T23:30
    kind: Literal["event", "work_order", "doc", "case", "data_quality", "current_state", "telemetry"]
    summary: str

class WorkOrderDraft(Strict):
    asset_id: str; action: str; maintenance_type: str; priority: str; role: str; rationale: str

class Diagnosis(Strict):
    asset_id: str
    tag: str
    observations: list[str]                   # what the data shows
    hypothesis: str                           # what it probably means
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]                   # every ID must exist in the retrieved context
    next_safe_check: str
    safety_note: str                          # from DOC-FIELD-SAFETY
    work_order_draft: Optional[WorkOrderDraft] = None
    model: str                                # e.g. "claude-opus-5-5" | "ollama:<name>" | "cache"
    cached: bool
    generated_at: datetime

class CameraSpec(Strict):
    kind: Literal["isometric"] = "isometric"
    position: Vec3
    target: Vec3
    fov: float = 35

class Snapshot(Strict):
    seq: int
    object_id: str
    asset_id: Optional[str] = None
    uri: str                                  # data/snapshots/0042_obj-0042_P-005.png
    camera: CameraSpec
    created_at: datetime
```

### 4.2 TypeScript — `contracts/ts/index.ts`

```ts
export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number]; // x, y, z, w
export type ClassGuess =
  | "CONTROL_VALVE" | "PROCESS_PUMP" | "ELECTRIC_MOTOR" | "PRESSURE_TRANSMITTER" | "VIBRATION_SENSOR"
  | "pipe" | "tank" | "boiler" | "cabinet" | "structure" | "other";
export type Status = "OK" | "WATCH" | "ALERT" | "UNKNOWN";
export type ConditionState = "healthy" | "watch" | "degraded" | "attention_required";

export interface OBB { center: Vec3; size: Vec3; rotation: Quat; }

export interface Proposal {
  proposal_id: string; rank: number; obb: OBB; point_count: number; point_indices_uri: string;
  label_guess: string; class_guess: ClassGuess; confidence_auto: number;
  status: "pending" | "approved" | "rejected" | "skipped";
}

export interface ApprovedObject {
  object_id: string; source_proposal_id: string; label: string; class_guess: ClassGuess;
  confidence_auto: number; obb: OBB; mesh_uri: string | null; point_indices_uri: string;
  asset_id: string | null; tag: string | null; mapping_confidence: number;
  mapping_method: "human_approved" | "procedural" | "none";
  approved_by: string; approved_at: string; snapshot_uri: string | null;
}

export interface SceneInfo {
  source_file: string; units: "scene_units" | "metres"; up_axis: "y";
  bounds_min: Vec3; bounds_max: Vec3; floor_y: number; grid_resolution: number; is_synthetic_metadata: boolean;
}
export interface SceneCounts { proposals: number; approved: number; rejected: number; skipped: number; bound: number; }
export interface SceneGraph {
  version: string; scene: SceneInfo; objects: ApprovedObject[]; target_object_id: string | null; counts: SceneCounts;
}

export interface CurrentState {
  health_score: number; condition_state: ConditionState; issue_code: string; issue_summary: string;
  urgency: string; recommended_next_check: string; model_confidence: number; last_updated: string; knowledge_doc_id: string;
}
export interface TelemetryRow {
  timestamp: string; process_pressure_bar?: number | null; process_flow_pct?: number | null;
  position_setpoint_pct?: number | null; position_actual_pct?: number | null; pneumatic_supply_bar?: number | null;
  stiction_index?: number | null; load_for_opening_pct?: number | null; vibration_mm_s?: number | null;
  bearing_temp_c?: number | null; motor_current_a?: number | null; speed_rpm?: number | null;
  sensor_bias?: number | null; signal_quality_pct?: number | null;
}
export interface EventRow {
  event_id: string; timestamp: string; event_type: string; severity: string; event_code: string;
  description: string; source: string; status: string;
}
export interface WorkOrderRow {
  work_order_id: string; opened_at: string; action: string; maintenance_type: string; priority: string;
  result: string; duration_h: number; downtime_h: number; role: string; knowledge_doc_id: string;
}
export interface DocRef { doc_id: string; title: string; scope: string; document_role: string; content?: string | null; }
export interface DataQualityRow { issue_id: string; issue_type: string; severity: string; source_sheet: string; recommended_handling: string; }

export interface AssetRecord {
  asset_id: string; tag: string; asset_class: string; area_id: string; area_name: string; process_context: string;
  criticality: string; installation_date: string; last_service_date: string; service_interval_days: number;
  connectivity_profile: string; current_state: CurrentState; status: Status;
  telemetry_window: TelemetryRow[]; events: EventRow[]; maintenance_history: WorkOrderRow[];
  documents: DocRef[]; data_quality: DataQualityRow[]; object_id: string | null; anchor: OBB | null;
}

export interface Route {
  target_asset_id: string; target_object_id: string; start: Vec3; waypoints: Vec3[]; length: number;
  min_clearance: number; grid_resolution: number; agent_radius: number;
  planner: "astar" | "manual_verified"; computed_at: string;
}

export interface CopilotQuery { asset_id: string; question?: string | null; mode?: "arrival" | "along_route"; demo_mode?: boolean | null; }
export interface Evidence {
  evidence_id: string;
  kind: "event" | "work_order" | "doc" | "case" | "data_quality" | "current_state" | "telemetry";
  summary: string;
}
export interface WorkOrderDraft { asset_id: string; action: string; maintenance_type: string; priority: string; role: string; rationale: string; }
export interface Diagnosis {
  asset_id: string; tag: string; observations: string[]; hypothesis: string; confidence: number;
  evidence_ids: string[]; next_safe_check: string; safety_note: string;
  work_order_draft: WorkOrderDraft | null; model: string; cached: boolean; generated_at: string;
}

export interface CameraSpec { kind: "isometric"; position: Vec3; target: Vec3; fov: number; }
export interface Snapshot { seq: number; object_id: string; asset_id: string | null; uri: string; camera: CameraSpec; created_at: string; }
```

`contracts/json-schema/*.json` is exported from the Pydantic models (`model_json_schema()`); `make check` fails if the TypeScript types drift (`scripts/check_contracts.py`).

---

## 5. API

Paths marked **pack** are the eight routes of the builder pack's `API_Contract` sheet `[SOURCE DATA]`, kept verbatim so the partner recognises them.

| Method | Route | Purpose | Backed by |
|---|---|---|---|
| GET | `/api/assets` **pack** | asset list with status, scene anchor, criticality | `Asset_Master` + `scene_graph.json` |
| GET | `/api/assets/{id}` **pack** | full `AssetRecord` | merge of all sheets |
| GET | `/api/assets/{id}/telemetry` **pack** | `TelemetryRow[]` 3-day sample | `Telemetry_Sample_3d` |
| GET | `/api/assets/{id}/events` **pack** | `EventRow[]` | `Alarms_Events` |
| GET | `/api/assets/{id}/documents` **pack** | `DocRef[]` (core docs with content + generated asset card) | `Knowledge_Docs`, `RAG_Corpus_Index` |
| GET | `/api/scene/anchors` **pack** | anchors with real coordinates after binding, `mapping_confidence` | `Scene_Anchors` rewritten by `M6` |
| POST | `/api/copilot/query` **pack** | `CopilotQuery` → `Diagnosis` (validated, cached in Demo Mode) | all sheets + `llm_client` |
| POST | `/api/work-orders/draft` **pack** | `Diagnosis` → `WorkOrderDraft` (draft only, never a control action) | `Maintenance_History` schema |
| GET | `/api/proposals/next` | next pending `Proposal` (by rank) | `proposals.json` |
| GET | `/api/proposals/{id}` | one proposal + its point indices URI | `proposals.json` |
| POST | `/api/proposals/{id}/approve` | body `{label, class_guess, asset_id\|null, approved_by}` → appends `ApprovedObject`, returns it with `seq` for the snapshot | `scene_graph.json` (file lock, atomic write) |
| POST | `/api/proposals/{id}/reject` · `/skip` · `/relabel` | state changes; `relabel` body `{label, class_guess}` | `proposals.json` |
| GET | `/api/scene/graph` | full `SceneGraph` | `scene_graph.json` |
| GET | `/api/scene/points` | `scene_points.bin` (binary, cached) | `data/derived/` |
| GET | `/api/scene/grid` | `grid.npz` as JSON (`occupied`, `blocked_human`, `blocked_robot`, origin, resolution, floor_y) | `data/derived/` |
| POST | `/api/snapshots` | multipart PNG + `{object_id, camera}` → `Snapshot` | `data/snapshots/` |
| GET | `/api/route?target=ASSET-017` | `Route` (computed on demand, cached per target) | `06_route.py` |
| GET / POST | `/api/demo-mode` | read / set `{enabled: bool}`; when enabled, copilot serves `data/cache/` only | env `DEMO_MODE` |

---

## 6. Copilot contract

**System prompt skeleton** (keep it stable for prompt caching; put the per-asset context in the user message):

```
You are the field-service copilot for a synthetic Valmet boiler room. Follow the evidence contract
from DOC-RAG-GUIDE: name the asset, cite telemetry/event/doc IDs, state confidence, distinguish
observation from hypothesis, and propose the next safe verification step.
Safety guardrail (DOC-FIELD-SAFETY, quote it in safety_note): "The assistant must not replace site
procedures, lockout/tagout, permits, OEM instructions or qualified personnel. Recommend verification
and escalation rather than autonomous physical action."
Rules: cite only IDs that appear in the CONTEXT block; if the evidence is insufficient say so and
lower confidence; never invent telemetry values; all data is synthetic.
```

**Python client** (`api/llm_client.py`) — only these SDK shapes are used:

```python
import anthropic
from a2b_contracts.models import Diagnosis

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / `ant auth login`

def diagnose(system_prompt: str, context_block: str, question: str) -> Diagnosis:
    response = client.messages.parse(
        model="claude-opus-5-5",                 # default; claude-haiku-5-5 / claude-sonnet-5-5 if the user wants speed
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"CONTEXT:\n{context_block}\n\nQUESTION: {question}"}],
        output_format=Diagnosis,                 # validated Pydantic instance
    )
    return response.parsed_output
```

- Thinking is always on for `claude-opus-5-5`; if latency matters use the raw form `client.messages.create(..., output_config={"effort": "low", "format": {"type": "json_schema", "schema": Diagnosis.model_json_schema()}})` and `json.loads` the first text block. Never use `budget_tokens`, never prefill an assistant turn.
- Refusal fallbacks can be enabled with `client.beta.messages.create(..., betas=["server-side-fallback-2026-07-01"], fallbacks="default")` if a request is ever declined.
- `OllamaClient` implements the same `diagnose()` signature against a local model (JSON-schema constrained output) for fully offline runs `[HYPOTHESIS]`; `CachedClient` wraps any client and reads `data/cache/diagnosis_<asset_id>.json` first.

**Citation validator** (`api/services/validator.py`) — runs on every `Diagnosis`, LLM or cache:

1. Build `allowed_ids` from the retrieved context: all `event_id`, `work_order_id`, `doc_id`, `case_id`, `issue_id` plus the synthetic IDs `CS:<asset_id>` and `TLM:<asset_id>:<start>/<end>` for the telemetry window actually sent.
2. Reject the response if any `evidence_id ∉ allowed_ids`, if `evidence_ids` is empty, or if `tag` ≠ the asset's tag. On rejection: retry once with the violation listed; on second failure return HTTP 422 `{"error": "uncited_diagnosis"}` and the UI shows "Insufficient evidence — no diagnosis" instead of prose.
3. Clamp `confidence` by data quality: if the asset has a `Data_Quality` row with `reduce_model_confidence`, cap at `min(confidence, 0.6)` `[SOURCE DATA — Data_Quality.recommended_handling]`.
4. Log `{asset_id, model, cached, evidence_ids, confidence}` to `docs/validator.log` for the honesty checklist.

**Demo Mode** (`M11`): `DEMO_MODE=1` or `POST /api/demo-mode {enabled: true}` → the copilot returns `data/cache/diagnosis_<asset_id>.json` for the three targets (`cached: true`, `model: "cache"`), routes come from committed `route_<asset_id>.json`, and the status bar shows `DEMO MODE · CACHED`. `07_demo_cache.py` generates the cache through the same validator so cached answers are as honest as live ones. The badge is never hidden.

---

## 7. Multi-agent division rules

| Agent | Owns | Never touches |
|---|---|---|
| **Claude Code** | `pipeline/`, `api/`, `Makefile`, `contracts/py/` | `web/` |
| **Cursor** | `web/`, `contracts/ts/` | `pipeline/`, `api/` |
| **Codex** | `tests/`, `scripts/`, data tooling (`check_counts.py`, `verify_cache.py`, `timelapse.sh`) | `web/src/`, `api/routers/` |
| **Antigravity** | `docs/` (slides, `video_script.md`, `technical_note.md`), repo `README.md` | anything under `pipeline/`, `api/`, `web/` |

- **Shared surface = `contracts/` only.** A change to any contract field requires (1) an entry in `docs/CONTRACT_CHANGES.md` (`date · who · field · why · migration`), (2) the Python **and** TypeScript edit in the same commit, (3) a ping to the owner of the other side. Until then, the field names in §4 are frozen.
- **Never edit another agent's folder.** If you need something from it, write the request as an issue line in `docs/REQUESTS.md` (`[web→api] need GET /api/scene/grid to include floor_y`).
- **Before handing off:** `make check` green, `data/scene_graph.json` valid against the schema (`scripts/check_counts.py`), no files written outside your folders except `data/derived/` (pipeline) and `data/snapshots/` (api).
- **Commits:** prefix `[pipe]`, `[api]`, `[web]`, `[docs]`, `[test]`, `[contract]`; one concern per commit; never commit `data/raw`, `.ply`, `.mp4`, keys or `node_modules`. Nobody force-pushes. Tag `v1.0-submission` at code freeze.
- **Resume protocol** (any agent, any time): read `AGENTS.md` → `data/scene_graph.json` (`counts`) → `pm_pack/05_Execution_Roadmap_and_Milestones.md` (current sprint + next gate) → `docs/REQUESTS.md` → your folder's `TODO.md`. State which `M`/`S` item you are on in your first message.

---

## 8. Conventions, definition of done, do-not list

**Conventions.** Python: `ruff` defaults, type hints everywhere, `pathlib`, `orjson` for JSON, every pipeline step `--in/--out` flags and idempotent, logs its counts (`kept 412 331 / 1 506 136`). TypeScript: strict mode, no `any`, scene code in `web/src/scene`, UI never computes geometry. Units are **scene units (u)** until `G1` is answered; `floor_y` and `grid_resolution` always come from `grid.npz`, never hard-coded in the web. Status is never colour-only. Every screen shows the `SYNTHETIC DATA` badge.

**Definition of done per MUST** (`02 §3` acceptance tests are the source; this is the artifact + command):

| ID | Artifact | Proves it |
|---|---|---|
| M1 | `data/derived/clean.npz`, `scene_points.bin` | `uv run pytest tests/test_clean.py` (count 350–500 k, bounds within ±20 u, y-up logged) |
| M2 | `grid.npz`, `walkable.png` | `tests/test_grid.py` (corridor cells free, boiler cells blocked) + visual check |
| M3 | `proposals.json` ≥ 40 | `scripts/check_counts.py --proposals` + 15/20 eyeball test logged in `docs/proposals_review.md` |
| M4 | curator at `/curate`, `scene_graph.json` growing | 10 approvals in < 4 min by a non-author; reload restores |
| M5 | `data/snapshots/NNNN_*.png` one per approval | `scripts/check_counts.py --snapshots` (count == approved) |
| M6 | `data/derived/xlsx/*.json`, `GET /api/assets/ASSET-017` | `tests/test_assets.py` (merged record, 30 bound after curation) |
| M7 | `route_ASSET-017.json` etc. | `tests/test_route.py` (no blocked cell, min clearance ≥ 0.25 u, < 1 s) |
| M8 | avatar run | `vitest` proximity test + 60 s recorded run |
| M9 | `Diagnosis` for three targets | `tests/test_copilot.py` (validator passes, ≥ 3 evidence IDs, < 8 s or cached) |
| M10 | walk mode | `vitest` grid-collision test + manual boiler test |
| M11 | `data/cache/*.json`, badge | `scripts/verify_cache.py` (byte-identical twice, Wi-Fi off) |
| M12 | `docs/video.mp4`, `docs/slides.pdf`, `README.md`, `docs/technical_note.md` | files exist, submission confirmation |

**Do not.**
- No fake numbers: every count, length, clearance and confidence on screen is read from `data/` at render time.
- No uncited diagnosis: the validator is not optional, not even in Demo Mode.
- No autonomous control actions, no "robot executes" wording — draft work orders only (`DOC-FIELD-SAFETY` `[SOURCE DATA]`).
- No UI polish before Gate 3; no new features after Gate 4; no code after the Sun 08:00 freeze.
- No geometry in the browser beyond collision lookups; the pipeline is the single source of truth.
- No metric claims ("3.2 m") until `G1` is answered — say "u".
- No VR footage unless recorded on the headset.
- Never modify `data/raw` / `Source-Data-Do-Not_change`.
