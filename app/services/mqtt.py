from contextlib import asynccontextmanager
from typing import Optional
import json

from asyncio_mqtt import Client

from app.models.settings import settings
from app.utils.logging import get_logger


logger = get_logger(__name__)
_client: Optional[Client] = None


async def init_mqtt() -> None:
    global _client
    _client = Client(
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        tls=None if not settings.mqtt_tls else {},
    )
    logger.info("mqtt_client_ready")


async def shutdown_mqtt() -> None:
    global _client
    _client = None


@asynccontextmanager
async def mqtt_subscribe(topic: str):
    if _client is None:
        raise RuntimeError("MQTT not initialized")
    async with _client as client:
        async with client.messages() as messages:
            await client.subscribe(topic)
            yield messages


async def publish(topic: str, payload: dict) -> None:
    """Publish a JSON payload to a topic using a short-lived connection.

    Security: avoids persistent connections; payload is JSON-serialized.
    """
    message = json.dumps(payload)
    async with Client(
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        tls=None if not settings.mqtt_tls else {},
    ) as client:
        await client.publish(topic, message, qos=1)
