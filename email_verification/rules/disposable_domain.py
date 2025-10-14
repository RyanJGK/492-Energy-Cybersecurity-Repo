from __future__ import annotations

from typing import Any, Dict, Set

from ..context import RuleContext
from ..rule_engine import Rule


DEFAULT_DOMAINS: Set[str] = {
    "mailinator.com",
    "tempmailo.com",
    "10minutemail.com",
    "guerrillamail.com",
    "sharklasers.com",
}


class DisposableDomainRule(Rule):
    name = "DisposableDomainRule"
    priority = 40

    def __init__(self, domains: Set[str] | None = None):
        super().__init__()
        self.domains = set(domains) if domains else set(DEFAULT_DOMAINS)

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        if event.get("type") != "AuthVerificationRequested":
            return
        email = event.get("email")
        if not email or "@" not in email:
            return
        domain = email.split("@", 1)[1].lower()
        if domain in self.domains:
            context.alert(
                severity="low",
                rule=self.name,
                message="Disposable or high-risk email domain",
                email=email,
                domain=domain,
            )
