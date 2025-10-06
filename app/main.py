from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.settings import settings
from app.utils.logging import configure_logging, get_logger


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", app=settings.app_name, env=settings.environment)

    # Lazy init optional integrations to preserve read-only defaults
    try:
        if settings.enable_db:
            from app.services.db import init_db

            await init_db()
            logger.info("db_initialized")
    except Exception as exc:  # noqa: BLE001
        logger.error("db_init_failed", error=str(exc))

    try:
        if settings.enable_mqtt:
            from app.services.mqtt import init_mqtt

            await init_mqtt()
            logger.info("mqtt_initialized")
    except Exception as exc:  # noqa: BLE001
        logger.error("mqtt_init_failed", error=str(exc))

    try:
        if settings.enable_ray:
            from app.services.ray_orchestrator import init_ray

            await init_ray()
            logger.info("ray_initialized")
    except Exception as exc:  # noqa: BLE001
        logger.error("ray_init_failed", error=str(exc))

    yield

    # Teardown
    try:
        if settings.enable_mqtt:
            from app.services.mqtt import shutdown_mqtt

            await shutdown_mqtt()
    except Exception as exc:  # noqa: BLE001
        logger.error("mqtt_shutdown_failed", error=str(exc))

    try:
        if settings.enable_db:
            from app.services.db import shutdown_db

            await shutdown_db()
    except Exception as exc:  # noqa: BLE001
        logger.error("db_shutdown_failed", error=str(exc))


app = FastAPI(title=settings.app_name, lifespan=lifespan)


# Routers
try:
    from app.api.routes import router as api_router
    from app.api.sim_routes import sim_router
    from app.api.ingest_routes import ingest_router
    from app.api.control_routes import control_router
    from app.api.replay_routes import replay_router

    app.include_router(api_router)
    app.include_router(sim_router)
    app.include_router(ingest_router)
    app.include_router(control_router)
    app.include_router(replay_router)
except Exception as exc:  # noqa: BLE001
    logger.error("router_init_failed", error=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode": "read-only" if settings.read_only_mode else "active"}
