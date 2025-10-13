from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from ..context import RuleContext
from ..rule_engine import Rule


class TokenExpiryRule(Rule):
    name = "TokenExpiryRule"
    priority = 20

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        if event.get("type") != "AuthVerificationRequested":
            return
        created_at_iso = event.get("token_created_at")
        confirmed_at_iso = event.get("timestamp")
        if not created_at_iso or not confirmed_at_iso:
            return

        created_at = datetime.fromisoformat(str(created_at_iso).replace("Z", "+00:00"))
        confirmed_at = datetime.fromisoformat(str(confirmed_at_iso).replace("Z", "+00:00"))

        default_hours = int(context.cfg.get("policy", {}).get("token_expiry", {}).get("email_verification_minutes", 24 * 60))
        max_age = timedelta(minutes=default_hours)

        if confirmed_at - created_at > max_age:
            context.alert(
                severity="medium",
                rule=self.name,
                message="Verification after token expiry window",
                token_age_minutes=int((confirmed_at - created_at).total_seconds() // 60),
                max_age_minutes=int(max_age.total_seconds() // 60),
                user_id=event.get("user_id"),
            )
