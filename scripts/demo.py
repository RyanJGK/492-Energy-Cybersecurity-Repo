#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Email verification imports
from email_verification.agent import EmailVerificationAgent
from email_verification.context import KVStore, Alert
from email_verification.rule_engine import RuleExecutor
from email_verification.rules.token_reuse import TokenReuseRule
from email_verification.rules.token_expiry import TokenExpiryRule
from email_verification.rules.velocity import VelocityRule
from email_verification.rules.disposable_domain import DisposableDomainRule
from email_verification.rules.geo_anomaly import GeoAnomalyRule
from email_verification.rules.dmarc_compliance import DMARCComplianceRule

# OT tracking imports
from schemas import OTProtocolFrame
from ot_collector.ot_tracking_agent import OTTrackingAgent


def load_csv_events(csv_path: str) -> List[Dict[str, Any]]:
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        events: List[Dict[str, Any]] = []
        for row in reader:
            e: Dict[str, Any] = dict(row)
            # Normalize to AuthVerificationRequested for demo purposes
            e["type"] = "AuthVerificationRequested"
            # Normalize fields
            if "timestamp" in e and e["timestamp"]:
                try:
                    # allow naive timestamps
                    datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    e["timestamp"] = datetime.now(timezone.utc).isoformat()
            else:
                e["timestamp"] = datetime.now(timezone.utc).isoformat()
            # token_created_at if present
            if e.get("token_created_at"):
                try:
                    datetime.fromisoformat(e["token_created_at"].replace("Z", "+00:00"))
                except Exception:
                    e["token_created_at"] = None
            # fabricate geo lat/lon from coarse geo field if provided like "US:City"
            geo = e.get("geo")
            if isinstance(geo, str) and ":" in geo:
                # assign a few canonical coordinates
                mapping = {
                    "US:New York": (40.7128, -74.0060),
                    "US:Los Angeles": (34.0522, -118.2437),
                    "GB:London": (51.5074, -0.1278),
                    "DE:Berlin": (52.5200, 13.4050),
                    "BR:São Paulo": (-23.5505, -46.6333),
                    "IN:Bengaluru": (12.9716, 77.5946),
                    "CN:Shanghai": (31.2304, 121.4737),
                    "RU:Moscow": (55.7558, 37.6173),
                    "CA:Toronto": (43.6532, -79.3832),
                    "AU:Sydney": (-33.8688, 151.2093),
                    "NL:Amsterdam": (52.3676, 4.9041),
                    "US:Seattle": (47.6062, -122.3321),
                    "US:New York": (40.7128, -74.0060),
                }
                latlon = mapping.get(geo)
                if latlon:
                    e["geo"] = {"lat": latlon[0], "lon": latlon[1]}
            events.append(e)
    return events


def email_demo(csv_path: str) -> int:
    alerts: List[Alert] = []

    def sink(alert: Alert) -> None:
        alerts.append(alert)
        print(json.dumps({
            "severity": alert.severity,
            "rule": alert.rule,
            "message": alert.message,
            **alert.details,
        }))

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
            "token_expiry": {"email_verification_minutes": 24 * 60},
        },
        "agent": {"max_batch": 50},
    }
    events = load_csv_events(csv_path)

    # Append synthetic scenarios to guarantee alerts across rules
    now = datetime.now(timezone.utc)
    # Token reuse
    events.extend([
        {
            "type": "AuthVerificationRequested",
            "user_id": "u-token",
            "email": "user@example.com",
            "ip": "1.2.3.4",
            "token": "tok123",
            "device_fingerprint": "dev-token",
            "timestamp": now.isoformat(),
            "token_created_at": (now - timedelta(minutes=5)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060},
        },
        {
            "type": "AuthVerificationRequested",
            "user_id": "u-token",
            "email": "user@example.com",
            "ip": "1.2.3.4",
            "token": "tok123",
            "device_fingerprint": "dev-token",
            "timestamp": (now + timedelta(seconds=1)).isoformat(),
            "token_created_at": (now - timedelta(minutes=5)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060},
        },
    ])

    # Velocity burst
    for i in range(60):
        events.append({
            "type": "AuthVerificationRequested",
            "user_id": f"u-vel-{i}",
            "email": f"u{i}@example.com",
            "ip": "9.9.9.9",
            "device_fingerprint": "dev-vel",
            "timestamp": (now + timedelta(seconds=i)).isoformat(),
            "token_created_at": (now - timedelta(minutes=1)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060},
        })

    # Geo anomaly with warmup
    for i in range(10):
        events.append({
            "type": "AuthVerificationRequested",
            "user_id": "u-geo",
            "email": "geo@example.com",
            "ip": "5.6.7.8",
            "device_fingerprint": "dev-geo",
            "timestamp": (now - timedelta(minutes=10 - i)).isoformat(),
            "token_created_at": (now - timedelta(minutes=30)).isoformat(),
            "geo": {"lat": 40.7128, "lon": -74.0060},
        })
    events.append({
        "type": "AuthVerificationRequested",
        "user_id": "u-geo",
        "email": "geo@example.com",
        "ip": "5.6.7.8",
        "device_fingerprint": "dev-geo",
        "timestamp": (now + timedelta(hours=1)).isoformat(),
        "token_created_at": (now - timedelta(minutes=30)).isoformat(),
        "geo": {"lat": 35.6762, "lon": 139.6503},
    })

    # Token expiry
    events.append({
        "type": "AuthVerificationRequested",
        "user_id": "u-exp",
        "email": "exp@example.com",
        "ip": "2.3.4.5",
        "device_fingerprint": "dev-exp",
        "timestamp": now.isoformat(),
        "token_created_at": (now - timedelta(days=2)).isoformat(),
        "geo": {"lat": 43.6532, "lon": -79.3832},
    })

    # Disposable domain
    events.append({
        "type": "AuthVerificationRequested",
        "user_id": "u-temp",
        "email": "foo@tempmailo.com",
        "ip": "3.4.5.6",
        "device_fingerprint": "dev-temp",
        "timestamp": now.isoformat(),
        "token_created_at": (now - timedelta(minutes=5)).isoformat(),
        "geo": {"lat": 52.5200, "lon": 13.4050},
    })

    # DMARC report
    events.append({
        "type": "DMARCAggregateReport",
        "domain": "example.com",
        "spf_aligned": False,
        "dkim_aligned": True,
        "failure_rate": 0.1,
    })
    agent = EmailVerificationAgent(consumer=None, rules=rules, cfg=cfg, kv=KVStore(), alert_sink=sink)
    agent.process_events(events)
    # print a small summary to stderr
    print(f"processed={agent.metrics.counters.get('events_processed', 0)} alerts={agent.metrics.counters.get('alerts_fired', 0)}", file=sys.stderr)
    return 0


def ot_demo() -> int:
    # Build a very small synthetic OT sequence
    agent = OTTrackingAgent()
    # Optional: preload baseline so UnknownFunctionCodeRule can fire
    agent.load_baseline([
        ("10.10.0.2", "10.10.0.10", "modbus", ["3", "4"]),
    ])
    # Load simple zones from config if present
    zones_path = os.path.join("config", "zones.yaml")
    if os.path.exists(zones_path):
        try:
            import yaml  # type: ignore
        except Exception:
            yaml = None  # type: ignore
        if yaml is not None:
            with open(zones_path) as f:
                data = yaml.safe_load(f)
                agent.load_zones(data, data.get("allowed_flows", []))

    now = datetime.now(timezone.utc)
    frames = [
        OTProtocolFrame(protocol="modbus", src_ip="10.10.0.2", dst_ip="10.10.0.10", func_code="3", addr=1, value="123", session_id="s1", timestamp=now),
        OTProtocolFrame(protocol="modbus", src_ip="10.10.0.2", dst_ip="10.10.0.10", func_code="4", addr=2, value="456", session_id="s1", timestamp=now),
        # Off-schedule write (func 6) later
        OTProtocolFrame(protocol="modbus", src_ip="10.10.0.2", dst_ip="10.10.0.10", func_code="6", addr=3, value="789", session_id="s1", timestamp=now.replace(minute=(now.minute + 10) % 60)),
        # Out-of-range value
        OTProtocolFrame(protocol="modbus", src_ip="10.10.0.2", dst_ip="10.10.0.10", func_code="3", addr=4, value="9999", session_id="s1", timestamp=now),
        # Unauthorized zonal flow if zones disallow
        OTProtocolFrame(protocol="dnp3", src_ip="10.0.1.5", dst_ip="192.168.100.20", func_code="write", addr=None, value=None, session_id="d1", timestamp=now),
    ]

    for fr in frames:
        alerts = agent.ingest_frame(fr)
        for a in alerts:
            print(json.dumps({
                "severity": a.severity,
                "rule": a.rule,
                "message": a.message,
                **a.details,
            }))
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Run local demos for this project")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_email = sub.add_parser("email", help="Run email verification agent demo over CSV")
    p_email.add_argument("--csv", default=os.path.join("data", "auth_events.csv"))

    sub.add_parser("ot", help="Run OT tracking agent synthetic demo")

    args = parser.parse_args(argv)
    if args.cmd == "email":
        return email_demo(args.csv)
    if args.cmd == "ot":
        return ot_demo()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
