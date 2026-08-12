"""Real RabbitMQ producer. Publishes the validated VISIREPORT_SCHEMA payload
to the durable topic exchange. If RabbitMQ is unreachable or the publish is
un-routable/un-confirmed, this raises - callers must treat that as a hard
failure (503), never as a silent success."""
import json
import logging

import aio_pika

from app.config import get_settings

logger = logging.getLogger("visireport.messaging")


class BrokerUnavailableError(RuntimeError):
    pass


async def publish_inspection_payload(payload: dict, routing_key: str = "inspection.validated") -> None:
    settings = get_settings()
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=5)
    except Exception as exc:
        logger.error("RabbitMQ connection failed: %s", exc)
        raise BrokerUnavailableError(f"Could not connect to RabbitMQ: {exc}") from exc

    try:
        async with connection:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.declare_exchange(
                settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True)
            await queue.bind(exchange, routing_key="inspection.#")

            message = aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            confirmation = await exchange.publish(message, routing_key=routing_key)
            logger.info(
                "Published inspection %s to %s (routing_key=%s)",
                payload.get("report_id"),
                settings.rabbitmq_exchange,
                routing_key,
            )
            return confirmation
    except aio_pika.exceptions.AMQPError as exc:
        logger.error("RabbitMQ publish failed: %s", exc)
        raise BrokerUnavailableError(f"Publish failed: {exc}") from exc


async def check_broker_health() -> dict:
    settings = get_settings()
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=3)
        async with connection:
            channel = await connection.channel()
            await channel.declare_exchange(
                settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True
            )
        return {"healthy": True, "detail": "connected"}
    except Exception as exc:
        return {"healthy": False, "detail": str(exc)}
