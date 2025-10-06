from typing import List

from fastapi import APIRouter, HTTPException

from app.models.settings import settings
from app.models.telemetry import TelemetryEnvelope
from app.services import db as db_service
from app.services import mqtt as mqtt_service
from app.services.policy import allow
from app.utils.logging import get_logger


logger = get_logger(__name__)

replay_router = APIRouter(prefix="/replay", tags=["replay"])


@replay_router.post("/batch")
async def replay_batch(
    events: List[TelemetryEnvelope],
    store: bool = False,
    publish: bool = False,
) -> dict:
    if (store or publish) and settings.read_only_mode:
        raise HTTPException(status_code=403, detail="read_only_mode: storage and publish disabled")

    if not await allow("replay", {"count": len(events), "store": store, "publish": publish}):
        raise HTTPException(status_code=403, detail="policy_denied")

    stored = 0
    published = 0

    if store and settings.enable_db:
        try:
            await db_service.fetch_one("SELECT 1")
            create_sql = (
                "CREATE TABLE IF NOT EXISTS telemetry("
                "device_id text not null, ts timestamptz not null, payload jsonb not null)"
            )
            await db_service.fetch_one(create_sql)
            insert_sql = "INSERT INTO telemetry(device_id, ts, payload) VALUES($1,$2,$3)"
            for ev in events:
                await db_service.fetch_one(insert_sql, ev.device_id, ev.ts, ev.model_dump())
                stored += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("replay_store_failed", error=str(exc))

    if publish and settings.enable_mqtt:
        try:
            for ev in events:
                topic = f"telemetry/{ev.device_id}"
                await mqtt_service.publish(topic, ev.model_dump())
                published += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("replay_publish_failed", error=str(exc))

    return {"accepted": len(events), "stored": stored, "published": published}
