import logging
import time
from datetime import datetime, timedelta, timezone

from email_verification.agent import EmailVerificationAgent
from email_verification.context import KVStore, Alert
from email_verification.rule_engine import RuleExecutor
from email_verification.rules.token_reuse import TokenReuseRule
from email_verification.rules.token_expiry import TokenExpiryRule
from email_verification.rules.velocity import VelocityRule
from email_verification.rules.disposable_domain import DisposableDomainRule
from email_verification.rules.geo_anomaly import GeoAnomalyRule
from email_verification.rules.dmarc_compliance import DMARCComplianceRule


class DummyConsumer:
    def __init__(self, events):
        self._events = list(events)

    def poll(self, timeout=1.0):
        if self._events:
            class Msg:
                def __init__(self, value):
                    self._value = value

                def value(self):
                    return self._value
            return Msg(self._events.pop(0))
        time.sleep(timeout)
        return None


def test_minimal_agent_happy_path():
    alerts = []

    def sink(alert: Alert):
        alerts.append(alert)

    now = datetime.now(timezone.utc)
    events = []
    # Token reuse scenario
    for i in range(2):
        events.append({
            "type": "AuthVerificationRequested",
            "user_id": "u1",
            "email": "user@example.com",
            "ip": "1.2.3.4",
            "token": "tok123",
            "device_fingerprint": "dev1",
            "timestamp": now.isoformat(),
            "token_created_at": (now - timedelta(minutes=5)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060}
        })

    # Velocity burst from same IP
    for i in range(60):
        events.append({
            "type": "AuthVerificationRequested",
            "user_id": f"u{i}",
            "email": f"u{i}@example.com",
            "ip": "1.2.3.4",
            "device_fingerprint": f"dev{i}",
            "timestamp": now.isoformat(),
            "token_created_at": (now - timedelta(minutes=1)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060}
        })

    # Geo anomaly (impossible travel)
    events.append({
        "type": "AuthVerificationRequested",
        "user_id": "u-geo",
        "email": "geo@example.com",
        "ip": "5.6.7.8",
        "device_fingerprint": "dev-geo",
        "timestamp": now.isoformat(),
        "token_created_at": (now - timedelta(minutes=1)).isoformat(),
        "geo": {"lat": 40.7128, "lon": -74.0060}
    })
    events.extend({
        "type": "AuthVerificationRequested",
        "user_id": "u-geo",
        "email": "geo@example.com",
        "ip": "5.6.7.8",
        "device_fingerprint": "dev-geo",
        "timestamp": (now + timedelta(hours=1)).isoformat(),
        "token_created_at": (now - timedelta(minutes=1)).isoformat(),
        "geo": {"lat": 35.6762, "lon": 139.6503}
    } for _ in range(10))  # warmup + detection

    # DMARC failing report
    events.append({
        "type": "DMARCAggregateReport",
        "domain": "example.com",
        "spf_aligned": False,
        "dkim_aligned": True,
        "failure_rate": 0.1
    })

    rules = [
        TokenReuseRule(),
        TokenExpiryRule(),
        VelocityRule(),
        DisposableDomainRule(domains={"tempmailo.com"}),
        GeoAnomalyRule(),
        DMARCComplianceRule(),
    ]

    cfg = {
        "policy": {
            "ip_rate_limits": {"window_seconds": 300, "max_auth_requests": 50},
            "token_expiry": {"email_verification_minutes": 24 * 60}
        },
        "agent": {"max_batch": 50}
    }

    agent = EmailVerificationAgent(consumer=DummyConsumer(events), rules=rules, cfg=cfg, alert_sink=sink, kv=KVStore(), logger=logging.getLogger("test"))

    # Run for a short period to process all events
    start = time.time()
    while time.time() - start < 3:
        agent.run()
        break

    # Validate alerts
    kinds = [a.rule for a in alerts]
    assert "TokenReuseRule" in kinds
    assert any(a.rule == "VelocityRule" and a.severity in ("low", "medium", "high") for a in alerts)
    assert any(a.rule == "GeoAnomalyRule" for a in alerts)
    assert any(a.rule == "DMARCComplianceRule" for a in alerts)
