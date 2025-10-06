from fastapi import APIRouter, HTTPException

from app.models.settings import settings
from app.models.telemetry import TelemetryEnvelope
from app.utils.logging import get_logger
from app.services import db as db_service
from app.services import mqtt as mqtt_service
from app.services.policy import allow


logger = get_logger(__name__)

ingest_router = APIRouter(prefix="/ingest", tags=["ingest"])


@ingest_router.post("/telemetry")
async def ingest_telemetry(
    envelope: TelemetryEnvelope,
    store: bool = False,
    publish: bool = False,
) -> dict:
    # Always allowed to parse and log; mutations require policy and non-read-only mode
    logger.info("telemetry_received", device_id=envelope.device_id, kind=envelope.data.__class__.__name__)

    if (store or publish) and settings.read_only_mode:
        raise HTTPException(status_code=403, detail="read_only_mode: storage and publish disabled")

    context = {"device_id": envelope.device_id, "store": store, "publish": publish}
    if not await allow("ingest", context):
        raise HTTPException(status_code=403, detail="policy_denied")

    stored = False
    published = False

    if store and settings.enable_db:
        try:
            # Minimal safe schema: (device_id text, ts timestamptz, payload jsonb)
            await db_service.fetch_one("SELECT 1")  # Ensure pool is healthy
            query = """
            INSERT INTO telemetry(device_id, ts, payload)
            VALUES($1, $2, $3)
            """
            # Lazy create table if missing (non-destructive)
            try:
                await db_service.fetch_one(query, envelope.device_id, envelope.ts, envelope.model_dump())
                stored = True
            except Exception:
                # Attempt to create minimal table and retry once
                create_sql = (
                    "CREATE TABLE IF NOT EXISTS telemetry("
                    "device_id text not null, ts timestamptz not null, payload jsonb not null)"
                )
                await db_service.fetch_one(create_sql)
                await db_service.fetch_one(query, envelope.device_id, envelope.ts, envelope.model_dump())
                stored = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("telemetry_store_failed", error=str(exc))

    if publish and settings.enable_mqtt:
        try:
            topic = f"telemetry/{envelope.device_id}"
            await mqtt_service.publish(topic, envelope.model_dump())
            published = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("telemetry_publish_failed", error=str(exc))

    return {"accepted": True, "stored": stored, "published": published}
