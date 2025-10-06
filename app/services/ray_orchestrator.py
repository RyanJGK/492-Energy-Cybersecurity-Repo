from typing import Optional

from app.models.settings import settings
from app.utils.logging import get_logger


logger = get_logger(__name__)
_ray_initialized: bool = False


async def init_ray() -> None:
    global _ray_initialized
    if settings.ray_address:
        try:
            import ray  # type: ignore

            ray.init(address=settings.ray_address)  # noqa: F821
        except Exception as exc:  # noqa: BLE001
            logger.error("ray_init_error", error=str(exc))
    _ray_initialized = True


def is_ray_ready() -> bool:
    return _ray_initialized
