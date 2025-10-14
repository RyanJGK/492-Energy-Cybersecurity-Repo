from __future__ import annotations

from typing import Any, Dict

from ..context import RuleContext
from ..rule_engine import Rule


class VelocityRule(Rule):
    name = "VelocityRule"
    priority = 30

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        if event.get("type") != "AuthVerificationRequested":
            return

        ip = event.get("ip")
        device = event.get("device_fingerprint") or "unknown"
        email = event.get("email")

        policy = context.cfg.get("policy", {})
        window_seconds = int(policy.get("ip_rate_limits", {}).get("window_seconds", 300))
        threshold = int(policy.get("ip_rate_limits", {}).get("max_auth_requests", 50))

        ip_count = context.kv.incr(f"vel:ip:{ip}", ttl_seconds=window_seconds)
        device_count = context.kv.incr(f"vel:device:{device}", ttl_seconds=window_seconds)
        email_count = context.kv.incr(f"vel:email:{email}", ttl_seconds=window_seconds)

        # Gentle backoff: emit lower severity first, escalate if sustained
        severity = None
        if ip_count > threshold or device_count > threshold or email_count > threshold:
            severity = "low"
        if ip_count > 2 * threshold or device_count > 2 * threshold or email_count > 2 * threshold:
            severity = "medium"
        if ip_count > 3 * threshold or device_count > 3 * threshold or email_count > 3 * threshold:
            severity = "high"

        if severity:
            context.alert(
                severity=severity,
                rule=self.name,
                message="Verification velocity exceeded",
                ip=ip,
                device=device,
                email=email,
                counts={"ip": ip_count, "device": device_count, "email": email_count},
                threshold=threshold,
                window_seconds=window_seconds,
            )
