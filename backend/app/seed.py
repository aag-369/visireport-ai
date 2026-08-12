"""Idempotent startup seed: creates the seed engineer user and (if a
training-run metrics file has been placed at weights/model_metrics.json)
a model_runs row so the System Performance tab reflects a real training
run rather than invented numbers. Run via `python -m app.seed`."""
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models.model_run import ModelRun
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visireport.seed")


async def seed_user(db) -> None:
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == settings.seed_engineer_email))
    if result.scalar_one_or_none() is not None:
        logger.info("Seed user already exists")
        return
    user = User(
        email=settings.seed_engineer_email,
        name="QA Engineer",
        role="engineer",
        hashed_password=hash_password(settings.seed_engineer_password),
    )
    db.add(user)
    logger.info("Created seed user %s", settings.seed_engineer_email)


async def seed_model_run(db) -> None:
    settings = get_settings()
    metrics_path = Path(settings.model_weights_path).parent / "model_metrics.json"
    if not metrics_path.exists():
        logger.warning("No model_metrics.json found next to weights - skipping model_runs seed")
        return

    existing = await db.execute(select(ModelRun))
    if existing.scalars().first() is not None:
        logger.info("model_runs already has data - skipping")
        return

    data = json.loads(metrics_path.read_text())
    run = ModelRun(
        model_version=data.get("model_version", "yolov8n-visireport"),
        map50=data["map50"],
        map50_95=data["map50_95"],
        precision=data["precision"],
        recall=data["recall"],
        per_class_metrics_json=json.dumps(data.get("per_class", {})),
        dataset=data.get("dataset", "DeepPCB"),
        epochs=data.get("epochs", 0),
        notes=data.get("notes", "CPU-only fine-tune; below paper SLA targets by design."),
    )
    db.add(run)
    logger.info("Seeded model_runs from %s", metrics_path)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_user(db)
        await seed_model_run(db)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
