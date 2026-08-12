export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Defect {
  defect_id: string;
  class: string;
  confidence: number;
  global_bbox: BBox;
  iso_severity: "CRITICAL" | "MAJOR" | "MINOR";
  tile_origin: [number, number];
  status: "PENDING" | "CONFIRMED" | "OVERRIDDEN";
  engineer_notes?: string | null;
  validated_by?: number | null;
  validated_at?: string | null;
}

export interface Inspection {
  id: number;
  report_id: string;
  board_id: string;
  inspection_timestamp: string;
  board_disposition: "CONFORMING" | "NONCONFORMING";
  schema_valid: boolean;
  cycle_time_ms: number;
  tile_size: number;
  overlap_margin: number;
  conf_threshold: number;
  iou_threshold: number;
  defects: Defect[];
  narrative_status: string | null;
  status: "PROCESSING" | "COMPLETE" | "FAILED";
  error_detail: string | null;
}

export interface CAPA {
  immediate_containment: string;
  root_cause_elimination: string;
  preventive_measure: string;
}

export interface Narrative {
  inspection_id: number;
  status: "PENDING" | "READY" | "FAILED";
  narrative_text: string | null;
  root_cause_text: string | null;
  capa: CAPA | null;
  llm_model_used: string | null;
  generated_at: string | null;
  error_detail: string | null;
}

export interface AuditEntry {
  id: number;
  inspection_id: number | null;
  actor: number | null;
  actor_name: string | null;
  action: string;
  defect_id: string | null;
  timestamp: string;
  detail: string | null;
}

export interface ModelMetrics {
  model_version: string;
  map50: number;
  map50_95: number;
  precision: number;
  recall: number;
  per_class_metrics_json: string | null;
  dataset: string;
  epochs: number;
  notes: string | null;
  trained_at: string;
}

export interface SystemStatus {
  vision_engine: Record<string, unknown>;
  message_broker: Record<string, unknown>;
  llm_engine: Record<string, unknown>;
  schema_validator: Record<string, unknown>;
  database: Record<string, unknown>;
}
