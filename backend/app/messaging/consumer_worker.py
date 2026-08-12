"""Standalone RabbitMQ consumer worker process (runs as its own Docker
service - see docker-compose.yml `worker`).

On each validated inspection message:
  1. parse + look up the inspection/defects in Postgres
  2. call the real LLM adapter to synthesize narrative + root-cause + CAPA
  3. persist the result (or the failure) to the `narratives` table
  4. push a "narrative_ready"/"narrative_failed" event over the shared
     WebSocket progress hub so the frontend updates live
"""
import asyncio
import json
import logging

import aio_pika
from sqlalchemy import select

from app.cognitive.llm_client import LLMAdapterError, generate_narrative
from app.config import get_settings
from app.core.db import AsyncSessionLocal
from app.models.inspection import Inspection
from app.models.narrative import Narrative
from app.ws.progress_hub import publish_external_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("visireport.worker")


async def handle_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        payload = json.loads(message.body.decode("utf-8"))
        report_id = payload.get("report_id")
        logger.info("Consumed message for report_id=%s", report_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Inspection).where(Inspection.report_id == report_id))
            inspection = result.scalar_one_or_none()
            if inspection is None:
                logger.error("Inspection not found for report_id=%s - dropping message", report_id)
                return

            narrative_result = await db.execute(
                select(Narrative).where(Narrative.inspection_id == inspection.id)
            )
            narrative = narrative_result.scalar_one_or_none()
            if narrative is None:
                narrative = Narrative(inspection_id=inspection.id, status="PENDING")
                db.add(narrative)
                await db.flush()

            try:
                generated = await generate_narrative(payload)
                narrative.narrative_text = generated["narrative_text"]
                narrative.root_cause_text = generated["root_cause_text"]
                narrative.capa_json = json.dumps(generated["capa"])
                narrative.llm_model_used = generated["model_used"]
                narrative.status = "READY"
                narrative.error_detail = None
                from datetime import datetime, timezone

                narrative.generated_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info("Narrative generated for report_id=%s", report_id)
                await publish_external_event(
                    inspection.id,
                    {"event": "narrative_ready", "inspection_id": inspection.id, "report_id": report_id},
                )
            except LLMAdapterError as exc:
                narrative.status = "FAILED"
                narrative.error_detail = str(exc)
                await db.commit()
                logger.error("Narrative generation failed for report_id=%s: %s", report_id, exc)
                await publish_external_event(
                    inspection.id,
                    {
                        "event": "narrative_failed",
                        "inspection_id": inspection.id,
                        "report_id": report_id,
                        "detail": str(exc),
                    },
                )


async def main() -> None:
    settings = get_settings()
    logger.info("Worker connecting to RabbitMQ at %s", settings.rabbitmq_url)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=4)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True)
        await queue.bind(exchange, routing_key="inspection.#")
        logger.info("Worker listening on queue=%s exchange=%s", settings.rabbitmq_queue, settings.rabbitmq_exchange)
        await queue.consume(handle_message)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
