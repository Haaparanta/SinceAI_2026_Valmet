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
