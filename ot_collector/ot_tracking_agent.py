from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from schemas import OTProtocolFrame
from .asset_manager import AssetManager


@dataclass
class Alert:
    severity: str
    rule: str
    message: str
    details: Dict[str, Any]


class Rule:
    name: str = "Rule"
    priority: int = 100

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:  # pragma: no cover
        return None


class NewMasterRule(Rule):
    name = "NewMasterRule"
    priority = 10

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:
        if frame.protocol not in {"modbus", "dnp3"}:
            return None
        src = frame.src_ip
        if src not in agent.known_masters:
            agent.known_masters.add(src)
            return Alert(
                severity="low",
                rule=self.name,
                message=f"New master {src} communicating with {frame.dst_ip}",
                details={"src": src, "dst": frame.dst_ip, "protocol": frame.protocol},
            )
        return None


class UnknownFunctionCodeRule(Rule):
    name = "UnknownFunctionCodeRule"
    priority = 20

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:
        baseline = agent.baseline.get((frame.src_ip, frame.dst_ip, frame.protocol))
        if not baseline:
            return None
        func = frame.func_code
        if func and func not in baseline.get("function_codes", set()):
            return Alert(
                severity="medium",
                rule=self.name,
                message="Unknown function code observed",
                details={"src": frame.src_ip, "dst": frame.dst_ip, "protocol": frame.protocol, "func": func},
            )
        return None


class OffScheduleWriteRule(Rule):
    name = "OffScheduleWriteRule"
    priority = 30

    WRITE_FUNCS = {"5", "6", "15", "16"}

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:
        if frame.protocol != "modbus" or not frame.func_code:
            return None
        if frame.func_code not in self.WRITE_FUNCS:
            return None
        stats = agent.asset_manager.flows.get((frame.src_ip, frame.dst_ip, frame.protocol))
        if not stats:
            return None
        period = stats.typical_period_seconds()
        if period is None:
            return None
        # If write occurs outside 2x normal polling period, raise
        last_ts = stats.timestamps[-1] if stats.timestamps else None
        if last_ts is None:
            return None
        delta = (frame.timestamp - last_ts).total_seconds()
        if delta > 2 * period:
            return Alert(
                severity="medium",
                rule=self.name,
                message="Off-schedule Modbus write detected",
                details={"src": frame.src_ip, "dst": frame.dst_ip, "func": frame.func_code, "delta_s": delta, "period_s": period},
            )
        return None


class OutOfRangeValueRule(Rule):
    name = "OutOfRangeValueRule"
    priority = 40

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:
        # Placeholder: would use learned ranges per address/tag; simple numeric check
        try:
            if frame.value is None:
                return None
            val = float(frame.value)
        except Exception:
            return None
        # Example physics limit for temperature
        if val > 400.0:
            return Alert(
                severity="high",
                rule=self.name,
                message="Out-of-range value detected",
                details={"dst": frame.dst_ip, "addr": frame.addr, "value": val},
            )
        return None


class UnauthorizedZonalFlowRule(Rule):
    name = "UnauthorizedZonalFlowRule"
    priority = 50

    def evaluate(self, frame: OTProtocolFrame, agent: "OTTrackingAgent") -> Optional[Alert]:
        src_zone = agent.zone_of(frame.src_ip)
        dst_zone = agent.zone_of(frame.dst_ip)
        if src_zone is None or dst_zone is None or src_zone == dst_zone:
            return None
        if (src_zone, dst_zone) in agent.allowed_zone_pairs:
            return None
        return Alert(
            severity="medium",
            rule=self.name,
            message="Unauthorized zonal flow",
            details={"src_ip": frame.src_ip, "dst_ip": frame.dst_ip, "src_zone": src_zone, "dst_zone": dst_zone},
        )


class OTTrackingAgent:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.asset_manager = AssetManager(logger=self.logger)
        self.rules: List[Rule] = [
            NewMasterRule(),
            UnknownFunctionCodeRule(),
            OffScheduleWriteRule(),
            OutOfRangeValueRule(),
            UnauthorizedZonalFlowRule(),
        ]
        self.known_masters: Set[str] = set()
        self.baseline: Dict[Tuple[str, str, str], Dict[str, Set[str]]] = {}
        self.zone_config: Dict[str, List[str]] = {}
        self.allowed_zone_pairs: Set[Tuple[str, str]] = set()

    def load_baseline(self, rows: Iterable[Tuple[str, str, str, List[str]]]) -> None:
        for src, dst, protocol, funcs in rows:
            self.baseline[(src, dst, protocol)] = {"function_codes": set(funcs)}

    def ingest_frame(self, frame: OTProtocolFrame) -> List[Alert]:
        alerts: List[Alert] = []
        # Update assets
        self.asset_manager.ingest(None, frame.src_ip, None, frame.dst_ip, frame.protocol, frame.func_code, frame.addr, frame.timestamp)
        # Evaluate rules
        for rule in self.rules:
            alert = rule.evaluate(frame, self)
            if alert:
                alerts.append(alert)
        return alerts

    def load_zones(self, zones: Dict[str, Any], allowed: List[Dict[str, str]]) -> None:
        self.zone_config = {z["name"]: z["cidrs"] for z in zones.get("zones", [])} if isinstance(zones, dict) else zones
        self.allowed_zone_pairs = {(f["src_zone"], f["dst_zone"]) for f in allowed}

    def zone_of(self, ip: str) -> Optional[str]:
        import ipaddress
        for zone_name, cidrs in self.zone_config.items():
            for cidr in cidrs:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr):
                    return zone_name
        return None
