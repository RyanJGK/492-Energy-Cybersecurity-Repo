from __future__ import annotations

import ipaddress
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, Iterable, List, Optional, Set, Tuple


@dataclass
class Asset:
    asset_id: str
    ip: Optional[str]
    mac: Optional[str]
    role: Optional[str]
    first_seen: datetime
    last_seen: datetime
    confidence: float = 0.5


@dataclass
class FlowKey:
    src: str
    dst: str
    protocol: str


@dataclass
class FlowStats:
    function_codes: Set[str] = field(default_factory=set)
    addresses: Set[int] = field(default_factory=set)
    timestamps: Deque[datetime] = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, func_code: Optional[str], addr: Optional[int], ts: datetime) -> None:
        if func_code:
            self.function_codes.add(str(func_code))
        if addr is not None:
            self.addresses.add(int(addr))
        self.timestamps.append(ts)

    def typical_period_seconds(self) -> Optional[float]:
        if len(self.timestamps) < 3:
            return None
        deltas = [ (t2 - t1).total_seconds() for t1, t2 in zip(list(self.timestamps)[:-1], list(self.timestamps)[1:]) ]
        deltas = [d for d in deltas if d > 0]
        if not deltas:
            return None
        deltas.sort()
        mid = len(deltas)//2
        return deltas[mid]


class AssetManager:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.assets_by_ip: Dict[str, Asset] = {}
        self.assets_by_mac: Dict[str, Asset] = {}
        self.flows: Dict[Tuple[str, str, str], FlowStats] = {}
        self.overrides: Dict[str, str] = {}  # asset_id -> role override

    def load_overrides(self, overrides: Dict[str, str]) -> None:
        self.overrides = overrides or {}

    def _get_or_create_asset(self, ip: Optional[str], mac: Optional[str], ts: datetime) -> Asset:
        key = ip or mac or "unknown"
        asset = None
        if ip and ip in self.assets_by_ip:
            asset = self.assets_by_ip[ip]
        elif mac and mac in self.assets_by_mac:
            asset = self.assets_by_mac[mac]
        else:
            asset = Asset(asset_id=key, ip=ip, mac=mac, role=None, first_seen=ts, last_seen=ts)
            if ip:
                self.assets_by_ip[ip] = asset
            if mac:
                self.assets_by_mac[mac] = asset
        asset.last_seen = ts
        return asset

    def _infer_role(self, src_ip: str, dst_ip: str, protocol: str, func_code: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        # Very rough heuristics
        server_role = None
        client_role = None
        if protocol == "modbus":
            # Destination likely PLC
            server_role = "plc"
            # Source likely HMI/engineering/master
            if func_code is not None and str(func_code) in {"5", "6", "15", "16"}:
                client_role = "engineering"
            else:
                client_role = "hmi"
        elif protocol == "dnp3":
            server_role = "rtu"
            client_role = "master"
        elif protocol in {"iec104", "iec61850"}:
            server_role = "substation_device"
            client_role = "control_center"
        return client_role, server_role

    def ingest(self, src_mac: Optional[str], src_ip: Optional[str], dst_mac: Optional[str], dst_ip: Optional[str], protocol: str, func_code: Optional[str], addr: Optional[int], ts: datetime) -> None:
        if not (src_ip and dst_ip):
            return
        src_asset = self._get_or_create_asset(src_ip, src_mac, ts)
        dst_asset = self._get_or_create_asset(dst_ip, dst_mac, ts)
        client_role, server_role = self._infer_role(src_ip, dst_ip, protocol, func_code)
        # Apply overrides if present
        if src_asset.asset_id in self.overrides:
            src_asset.role = self.overrides[src_asset.asset_id]
        elif client_role:
            src_asset.role = src_asset.role or client_role
        if dst_asset.asset_id in self.overrides:
            dst_asset.role = self.overrides[dst_asset.asset_id]
        elif server_role:
            dst_asset.role = dst_asset.role or server_role

        # Confidence bump on repeated observations
        src_asset.confidence = min(1.0, src_asset.confidence + 0.02)
        dst_asset.confidence = min(1.0, dst_asset.confidence + 0.02)

        key = (src_ip, dst_ip, protocol)
        stats = self.flows.get(key)
        if not stats:
            stats = FlowStats()
            self.flows[key] = stats
        stats.record(func_code, addr, ts)

    def export_inventory_rows(self) -> List[Tuple[str, Optional[str], Optional[str], Optional[str], datetime, datetime, float]]:
        rows: List[Tuple[str, Optional[str], Optional[str], Optional[str], datetime, datetime, float]] = []
        for asset in {**self.assets_by_ip, **self.assets_by_mac}.values():
            rows.append((asset.asset_id, asset.ip, asset.mac, asset.role, asset.first_seen, asset.last_seen, asset.confidence))
        # Deduplicate
        dedup: Dict[str, Tuple] = {}
        for r in rows:
            dedup[r[0]] = r
        return list(dedup.values())

    def export_baseline_rows(self) -> List[Tuple[str, str, str, List[str], List[int], Optional[float]]]:
        rows: List[Tuple[str, str, str, List[str], List[int], Optional[float]]] = []
        for (src, dst, protocol), stats in self.flows.items():
            rows.append((src, dst, protocol, sorted(stats.function_codes), sorted(stats.addresses), stats.typical_period_seconds()))
        return rows

    def generate_policy_yaml(self) -> str:
        import yaml  # type: ignore
        policy: Dict[str, Any] = {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "flows": []}
        for (src, dst, protocol), stats in self.flows.items():
            policy["flows"].append({
                "src": src,
                "dst": dst,
                "protocol": protocol,
                "function_codes": sorted(stats.function_codes),
                "address_ranges": self._address_ranges(sorted(stats.addresses)),
                "typical_period": stats.typical_period_seconds(),
            })
        return yaml.dump(policy, sort_keys=False)

    @staticmethod
    def _address_ranges(addrs: List[int]) -> List[Dict[str, int]]:
        if not addrs:
            return []
        ranges = []
        start = prev = addrs[0]
        for a in addrs[1:]:
            if a == prev + 1:
                prev = a
            else:
                ranges.append({"start": start, "end": prev})
                start = prev = a
        ranges.append({"start": start, "end": prev})
        return ranges
