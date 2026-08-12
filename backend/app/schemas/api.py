from datetime import datetime

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


# ── Boards ───────────────────────────────────────────────────────────────
class BoardCreate(BaseModel):
    board_id: str | None = None


class BoardResponse(BaseModel):
    id: int
    board_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Defects ──────────────────────────────────────────────────────────────
class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class DefectResponse(BaseModel):
    defect_id: str
    defect_class: str = Field(alias="class")
    confidence: float
    global_bbox: BBox
    iso_severity: str
    tile_origin: list[int]
    status: str
    engineer_notes: str | None = None
    validated_by: int | None = None
    validated_at: datetime | None = None

    class Config:
        populate_by_name = True


class DefectPatch(BaseModel):
    status: str = Field(pattern="^(CONFIRMED|OVERRIDDEN|PENDING)$")
    engineer_notes: str | None = None


# ── Inspections ──────────────────────────────────────────────────────────
class InspectionResponse(BaseModel):
    id: int
    report_id: str
    board_id: str
    inspection_timestamp: datetime
    board_disposition: str
    schema_valid: bool
    cycle_time_ms: int
    tile_size: int
    overlap_margin: int
    conf_threshold: float
    iou_threshold: float
    defects: list[DefectResponse]
    narrative_status: str | None = None
    status: str = "COMPLETE"
    error_detail: str | None = None


# ── Narrative ────────────────────────────────────────────────────────────
class CAPASection(BaseModel):
    immediate_containment: str
    root_cause_elimination: str
    preventive_measure: str


class NarrativeResponse(BaseModel):
    inspection_id: int
    status: str
    narrative_text: str | None = None
    root_cause_text: str | None = None
    capa: CAPASection | None = None
    llm_model_used: str | None = None
    generated_at: datetime | None = None
    error_detail: str | None = None


# ── Audit log ────────────────────────────────────────────────────────────
class AuditLogEntry(BaseModel):
    id: int
    inspection_id: int | None
    actor: int | None
    actor_name: str | None = None
    action: str
    defect_id: str | None
    timestamp: datetime
    detail: str | None

    class Config:
        from_attributes = True


# ── System / model metrics ─────────────────────────────────────────────
class ModelMetricsResponse(BaseModel):
    model_version: str
    map50: float
    map50_95: float
    precision: float
    recall: float
    per_class_metrics_json: str | None = None
    dataset: str
    epochs: int
    notes: str | None
    trained_at: datetime


class SystemStatusResponse(BaseModel):
    vision_engine: dict
    message_broker: dict
    llm_engine: dict
    schema_validator: dict
    database: dict


class HealthResponse(BaseModel):
    status: str
    checks: dict
