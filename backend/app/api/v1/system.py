import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cognitive.llm_client import check_llm_health
from app.core.db import get_db
from app.core.security import get_current_user
from app.messaging.producer import check_broker_health
from app.models.model_run import ModelRun
from app.models.user import User
from app.schemas.api import HealthResponse, ModelMetricsResponse, SystemStatusResponse
from app.vision.inference import YoloEngine

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    checks = {}

    try:
        await db.execute(select(1))
        checks["database"] = {"healthy": True}
    except Exception as exc:
        checks["database"] = {"healthy": False, "detail": str(exc)}

    checks["message_broker"] = await check_broker_health()

    engine = YoloEngine.instance()
    engine.load()
    checks["vision_engine"] = engine.status

    checks["llm_engine"] = await check_llm_health()

    overall = "ok" if all(c.get("healthy", c.get("ready", False)) for c in checks.values()) else "degraded"
    return HealthResponse(status=overall, checks=checks)


@router.get("/model/metrics", response_model=ModelMetricsResponse)
async def model_metrics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(ModelRun).order_by(ModelRun.trained_at.desc()).limit(1))
    run = result.scalar_one_or_none()
    if run is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="No model_runs record found - has training been recorded?")
    return ModelMetricsResponse(
        model_version=run.model_version,
        map50=run.map50,
        map50_95=run.map50_95,
        precision=run.precision,
        recall=run.recall,
        per_class_metrics_json=run.per_class_metrics_json,
        dataset=run.dataset,
        epochs=int(run.epochs),
        notes=run.notes,
        trained_at=run.trained_at,
    )


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    engine = YoloEngine.instance()
    engine.load()

    try:
        await db.execute(select(1))
        db_status = {"healthy": True}
    except Exception as exc:
        db_status = {"healthy": False, "detail": str(exc)}

    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()

    return SystemStatusResponse(
        vision_engine={**engine.status, "cpu_percent": cpu},
        message_broker=await check_broker_health(),
        llm_engine=await check_llm_health(),
        schema_validator={"healthy": True, "detail": "jsonschema validator active"},
        database={**db_status, "memory_percent": mem.percent},
    )
