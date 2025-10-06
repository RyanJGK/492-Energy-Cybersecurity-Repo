from typing import Any, Dict

import httpx

from app.models.settings import settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


async def allow(action: str, context: Dict[str, Any]) -> bool:
    """Query OPA for authorization decision.

    Fallback: use settings.allowed_actions if OPA is unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            payload = {"input": {"action": action, "context": context}}
            resp = await client.post(settings.opa_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Flexible parsing for common OPA response shapes
            if isinstance(data, dict):
                if "result" in data and isinstance(data["result"], bool):
                    return bool(data["result"])  # type: ignore[no-any-return]
                if "result" in data and isinstance(data["result"], dict):
                    inner = data["result"]
                    if "allow" in inner:
                        return bool(inner["allow"])  # type: ignore[no-any-return]
            logger.warning("opa_unexpected_response", data=data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("opa_query_failed", error=str(exc))
    return action in settings.allowed_actions
