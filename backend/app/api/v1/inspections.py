import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from jsonschema import ValidationError, validate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cognitive.llm_client import generate_narrative, LLMAdapterError
from app.config import get_settings
from app.core.db import get_db
from app.core.ids import new_defect_id, new_report_id
from app.core.payload import build_inspection_payload
from app.core.security import get_current_user
from app.messaging.producer import BrokerUnavailableError, publish_inspection_payload
from app.models.audit_log import AuditLog
from app.models.board import Board
from app.models.defect import Defect
from app.models.inspection import Inspection
from app.models.narrative import Narrative
from app.models.user import User
from app.reporting.pdf_generator import build_ncr_pdf
from app.vision.annotate import annotate_image
from app.vision.tiling import GlobalDetection, compute_tiles
from app.schemas.api import CAPASection, InspectionResponse, NarrativeResponse
from app.schemas.visireport_schema import DEFECT_TAXONOMY, VISIREPORT_SCHEMA
from app.vision.inference import ModelNotAvailableError, run_tiled_inference
from app.ws.progress_hub import publish_external_event

logger = logging.getLogger("visireport.api.inspections")
router = APIRouter(tags=["inspections"])

settings = get_settings()

# Strong references to in-flight background inference tasks, so they are
# not garbage-collected mid-run (asyncio only holds a weak ref otherwise).
_background_tasks: set[asyncio.Task] = set()


def _track_task(task: asyncio.Task) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _load_inspection(db: AsyncSession, inspection_id: int) -> Inspection:
    result = await db.execute(
        select(Inspection)
        .options(selectinload(Inspection.defects), selectinload(Inspection.board), selectinload(Inspection.narrative))
        .where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection


def _inspection_to_response(inspection: Inspection) -> InspectionResponse:
    payload = build_inspection_payload(inspection, inspection.defects)
    narrative_status = inspection.narrative.status if inspection.narrative else None
    return InspectionResponse(
        id=inspection.id,
        report_id=inspection.report_id,
        board_id=payload["board_id"],
        inspection_timestamp=inspection.inspection_timestamp,
        board_disposition=inspection.board_disposition,
        schema_valid=inspection.schema_valid,
        cycle_time_ms=inspection.cycle_time_ms,
        tile_size=inspection.tile_size,
        overlap_margin=inspection.overlap_margin,
        conf_threshold=inspection.conf_threshold,
        iou_threshold=inspection.iou_threshold,
        defects=payload["defects"],
        narrative_status=narrative_status,
        status=inspection.status,
        error_detail=inspection.error_detail,
    )


async def _process_inspection(
    inspection_id: int,
    image: np.ndarray,
    tile_size: int,
    overlap: int,
    conf_threshold: float,
    iou_threshold: float,
    user_id: int,
) -> None:
    """Runs the real tiling + YOLO inference off the event loop thread,
    streaming a WS event after every tile, then persists results, validates
    the schema, and publishes to RabbitMQ. Runs as a background asyncio task
    so the HTTP response returns immediately with the new inspection_id."""
    from app.core.db import AsyncSessionLocal

    loop = asyncio.get_running_loop()
    report_id = None

    def progress_cb(event: dict):
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                publish_external_event(inspection_id, {**event, "phase": "inference"})
            )
        )

    async with AsyncSessionLocal() as db:
        try:
            merged, tile_stats, cycle_time_ms = await asyncio.to_thread(
                run_tiled_inference, image, tile_size, overlap, conf_threshold, iou_threshold, progress_cb
            )
        except ModelNotAvailableError as exc:
            result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
            inspection = result.scalar_one()
            inspection.status = "FAILED"
            inspection.error_detail = f"Vision engine unavailable: {exc}"
            await db.commit()
            await publish_external_event(inspection_id, {"event": "inspection_failed", "detail": inspection.error_detail})
            return

        result = await db.execute(
            select(Inspection).options(selectinload(Inspection.board)).where(Inspection.id == inspection_id)
        )
        inspection = result.scalar_one()
        inspection.cycle_time_ms = cycle_time_ms
        inspection.board_disposition = "NONCONFORMING" if merged else "CONFORMING"

        defects: list[Defect] = []
        for idx, d in enumerate(merged, start=1):
            _, default_severity = DEFECT_TAXONOMY.get(d.cls, (d.cls, "MINOR"))
            defect = Defect(
                inspection_id=inspection.id,
                defect_id=new_defect_id(inspection.id * 1000 + idx),
                defect_class=d.cls,
                confidence=d.confidence,
                bbox_x=d.x,
                bbox_y=d.y,
                bbox_w=d.w,
                bbox_h=d.h,
                iso_severity=default_severity,
                tile_origin_row=d.tile_row,
                tile_origin_col=d.tile_col,
                status="PENDING",
            )
            db.add(defect)
            defects.append(defect)
        await db.flush()

        payload = build_inspection_payload(inspection, defects)
        try:
            validate(instance=payload, schema=VISIREPORT_SCHEMA)
            inspection.schema_valid = True
        except ValidationError as exc:
            inspection.schema_valid = False
            inspection.status = "FAILED"
            inspection.error_detail = f"VISIREPORT_SCHEMA validation failed: {exc.message}"
            await db.commit()
            await publish_external_event(inspection_id, {"event": "inspection_failed", "detail": inspection.error_detail})
            return

        narrative = Narrative(inspection_id=inspection.id, status="PENDING")
        db.add(narrative)
        db.add(
            AuditLog(
                inspection_id=inspection.id,
                actor=user_id,
                action="INSPECTION_CREATED",
                detail=f"{len(defects)} defect(s) detected across {len(tile_stats)} tile(s).",
            )
        )
        inspection.status = "COMPLETE"
        await db.commit()
        await publish_external_event(
            inspection_id,
            {"event": "inference_complete", "defect_count": len(defects), "tile_count": len(tile_stats)},
        )

        try:
            await publish_inspection_payload(payload)
            db.add(
                AuditLog(
                    inspection_id=inspection.id,
                    actor=user_id,
                    action="PAYLOAD_PUBLISHED",
                    detail="Published validated payload to RabbitMQ exchange.",
                )
            )
            await db.commit()
            await publish_external_event(inspection_id, {"event": "queue_dispatched"})
        except BrokerUnavailableError as exc:
            db.add(
                AuditLog(
                    inspection_id=inspection.id, actor=user_id, action="PAYLOAD_PUBLISH_FAILED", detail=str(exc)
                )
            )
            await db.commit()
            await publish_external_event(inspection_id, {"event": "queue_dispatch_failed", "detail": str(exc)})


@router.post("/boards/{board_id}/inspections", response_model=InspectionResponse, status_code=202)
async def create_inspection(
    board_id: str,
    file: UploadFile = File(...),
    tile_size: int = settings.default_tile_size,
    overlap: int = settings.default_tile_overlap,
    conf_threshold: float = settings.default_conf_threshold,
    iou_threshold: float = settings.default_iou_threshold,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    board_result = await db.execute(select(Board).where(Board.board_id == board_id))
    board = board_result.scalar_one_or_none()
    if board is None:
        board = Board(board_id=board_id)
        db.add(board)
        await db.flush()

    raw_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {settings.max_upload_mb}MB limit")

    npimg = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="Uploaded file is not a decodable image")

    h, w = image.shape[:2]
    if max(h, w) > settings.max_image_dim:
        raise HTTPException(status_code=422, detail=f"Image exceeds max dimension of {settings.max_image_dim}px")

    # Fail fast (before creating any DB rows) if the vision engine has no
    # weights loaded - never silently fall back to fake detections.
    from app.vision.inference import YoloEngine

    engine = YoloEngine.instance()
    engine.load()
    if not engine.is_ready:
        raise HTTPException(status_code=503, detail=f"Vision engine unavailable: {engine.status['error']}")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_filename = f"{uuid.uuid4().hex}.jpg"
    image_path = upload_dir / image_filename
    cv2.imwrite(str(image_path), image)

    inspection = Inspection(
        report_id=new_report_id(),
        board_id=board.id,
        image_path=str(image_path),
        tile_size=tile_size,
        overlap_margin=overlap,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        board_disposition="CONFORMING",
        schema_valid=False,
        cycle_time_ms=0,
        status="PROCESSING",
        created_by=user.id,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    _track_task(
        asyncio.create_task(
            _process_inspection(inspection.id, image, tile_size, overlap, conf_threshold, iou_threshold, user.id)
        )
    )

    inspection = await _load_inspection(db, inspection.id)
    return _inspection_to_response(inspection)


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(inspection_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = await _load_inspection(db, inspection_id)
    return _inspection_to_response(inspection)


@router.get("/inspections/{inspection_id}/defects")
async def list_defects(
    inspection_id: int,
    defect_class: str | None = None,
    min_confidence: float | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspection = await _load_inspection(db, inspection_id)
    payload = build_inspection_payload(inspection, inspection.defects)
    defects = payload["defects"]
    if defect_class:
        defects = [d for d in defects if d["class"] == defect_class]
    if min_confidence is not None:
        defects = [d for d in defects if d["confidence"] >= min_confidence]
    if status_filter:
        defects = [d for d in defects if d["status"] == status_filter]
    if search:
        defects = [d for d in defects if search.lower() in d["defect_id"].lower()]
    return {"inspection_id": inspection_id, "count": len(defects), "defects": defects}


@router.get("/inspections/{inspection_id}/narrative", response_model=NarrativeResponse)
async def get_narrative(inspection_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = await _load_inspection(db, inspection_id)
    narrative = inspection.narrative
    if narrative is None:
        raise HTTPException(status_code=404, detail="Narrative not found for this inspection")
    capa = None
    if narrative.capa_json:
        capa = CAPASection(**json.loads(narrative.capa_json))
    return NarrativeResponse(
        inspection_id=inspection_id,
        status=narrative.status,
        narrative_text=narrative.narrative_text,
        root_cause_text=narrative.root_cause_text,
        capa=capa,
        llm_model_used=narrative.llm_model_used,
        generated_at=narrative.generated_at,
        error_detail=narrative.error_detail,
    )


@router.post("/inspections/{inspection_id}/narrative/regenerate", response_model=NarrativeResponse)
async def regenerate_narrative(
    inspection_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    inspection = await _load_inspection(db, inspection_id)
    payload = build_inspection_payload(inspection, inspection.defects)
    narrative = inspection.narrative
    if narrative is None:
        narrative = Narrative(inspection_id=inspection.id, status="PENDING")
        db.add(narrative)
        await db.flush()

    logger.info("Live narrative regenerate requested for report_id=%s", inspection.report_id)
    try:
        generated = await generate_narrative(payload)
        narrative.narrative_text = generated["narrative_text"]
        narrative.root_cause_text = generated["root_cause_text"]
        narrative.capa_json = json.dumps(generated["capa"])
        narrative.llm_model_used = generated["model_used"]
        narrative.status = "READY"
        narrative.error_detail = None
        narrative.generated_at = datetime.now(timezone.utc)
        audit = AuditLog(inspection_id=inspection.id, actor=user.id, action="NARRATIVE_REGENERATED")
        db.add(audit)
        await db.commit()
    except LLMAdapterError as exc:
        narrative.status = "FAILED"
        narrative.error_detail = str(exc)
        await db.commit()
        raise HTTPException(status_code=503, detail=f"LLM narrative generation failed: {exc}")

    capa = CAPASection(**json.loads(narrative.capa_json)) if narrative.capa_json else None
    return NarrativeResponse(
        inspection_id=inspection_id,
        status=narrative.status,
        narrative_text=narrative.narrative_text,
        root_cause_text=narrative.root_cause_text,
        capa=capa,
        llm_model_used=narrative.llm_model_used,
        generated_at=narrative.generated_at,
        error_detail=narrative.error_detail,
    )


@router.get("/inspections/{inspection_id}/image")
async def get_annotated_image(
    inspection_id: int,
    grid: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Serves the uploaded board image re-annotated with the persisted
    defect bounding boxes + tile grid, for the Inspection viewport."""
    inspection = await _load_inspection(db, inspection_id)
    image = cv2.imread(inspection.image_path)
    if image is None:
        raise HTTPException(status_code=404, detail="Source image not found on disk")

    h, w = image.shape[:2]
    tile_grid = []
    if grid:
        tiles = compute_tiles(w, h, inspection.tile_size, inspection.overlap_margin)
        tile_grid = [{"x0": t.x0, "y0": t.y0, "x1": t.x1, "y1": t.y1} for t in tiles]

    detections = [
        GlobalDetection(
            cls=d.defect_class,
            confidence=d.confidence,
            x=d.bbox_x,
            y=d.bbox_y,
            w=d.bbox_w,
            h=d.bbox_h,
            tile_row=d.tile_origin_row,
            tile_col=d.tile_origin_col,
        )
        for d in inspection.defects
    ]
    annotated = annotate_image(image, detections, tile_grid)
    ok, buf = cv2.imencode(".jpg", annotated)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.get("/inspections/{inspection_id}/report.pdf")
async def get_report_pdf(inspection_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = await _load_inspection(db, inspection_id)
    payload = build_inspection_payload(inspection, inspection.defects)
    narrative_dict = None
    if inspection.narrative:
        capa = json.loads(inspection.narrative.capa_json) if inspection.narrative.capa_json else None
        narrative_dict = {
            "status": inspection.narrative.status,
            "narrative_text": inspection.narrative.narrative_text,
            "root_cause_text": inspection.narrative.root_cause_text,
            "capa": capa,
        }
    payload["cycle_time_ms"] = inspection.cycle_time_ms
    payload["schema_valid"] = inspection.schema_valid
    pdf_bytes = build_ncr_pdf(payload, narrative_dict)

    audit = AuditLog(inspection_id=inspection.id, actor=user.id, action="REPORT_PDF_EXPORTED")
    db.add(audit)
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{inspection.report_id}.pdf"'},
    )
