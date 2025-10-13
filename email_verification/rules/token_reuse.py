from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict

from ..context import RuleContext
from ..rule_engine import Rule


class TokenReuseRule(Rule):
    name = "TokenReuseRule"
    priority = 10

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        if event.get("type") != "AuthVerificationRequested":
            return
        token = event.get("token")
        user_id = event.get("user_id")
        if not token:
            return

        window_seconds = int(context.cfg.get("policy", {}).get("ip_rate_limits", {}).get("window_seconds", 300))
        token_hash = hashlib.sha256(str(token).encode()).hexdigest()
        key = f"token_reuse:{token_hash}"
        count = context.kv.incr(key, ttl_seconds=window_seconds)
        if count > 1:
            context.logger.info("Token reuse detected: token_hash=%s count=%s user_id=%s", token_hash, count, user_id)
            context.alert(
                severity="medium",
                rule=self.name,
                message="Verification token reused",
                token_hash=token_hash,
                count=count,
                user_id=user_id,
            )
