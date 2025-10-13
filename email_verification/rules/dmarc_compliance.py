from __future__ import annotations

from typing import Any, Dict

from ..context import RuleContext
from ..rule_engine import Rule


class DMARCComplianceRule(Rule):
    name = "DMARCComplianceRule"
    priority = 60

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        # This rule is driven by DMARC aggregate report ingestion events
        if event.get("type") != "DMARCAggregateReport":
            return
        domain = event.get("domain")
        spf_aligned = bool(event.get("spf_aligned"))
        dkim_aligned = bool(event.get("dkim_aligned"))
        failure_rate = float(event.get("failure_rate", 0.0))

        if not (spf_aligned and dkim_aligned):
            severity = "low" if failure_rate < 0.05 else "medium" if failure_rate < 0.15 else "high"
            context.alert(
                severity=severity,
                rule=self.name,
                message="DMARC alignment failing",
                domain=domain,
                spf_aligned=spf_aligned,
                dkim_aligned=dkim_aligned,
                failure_rate=failure_rate,
            )
