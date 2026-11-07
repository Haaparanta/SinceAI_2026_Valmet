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
