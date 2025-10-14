from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from ipaddress import ip_address
from typing import Optional, Literal, Any, Dict

ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _ensure_iso8601(dt: datetime) -> str:
    if dt.tzinfo is None:
        # Assume UTC if naive
        return dt.strftime(ISO8601_FORMAT)
    return dt.astimezone(tz=None).strftime(ISO8601_FORMAT)


def _validate_ip(value: str) -> str:
    try:
        ip_address(value)
    except ValueError as exc:
        raise ValueError(f"Invalid IP address: {value}") from exc
    return value


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _validate_timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("timestamp must be a datetime instance")
    return value


def _to_json(obj: Any) -> str:
    return json.dumps(asdict(obj), separators=(",", ":"))


def _from_json(cls, data: str):
    payload = json.loads(data)
    return cls(**payload)


@dataclass(frozen=True)
class AuthVerificationRequested:
    user_id: str
    email: str
    ip: str
    user_agent: str
    geo: Optional[str]
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.user_id, "user_id")
        _non_empty(self.email, "email")
        _validate_ip(self.ip)
        _non_empty(self.user_agent, "user_agent")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "AuthVerificationRequested",
            "user_id": self.user_id,
            "email": self.email,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "geo": self.geo,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "AuthVerificationRequested":
        payload = json.loads(data)
        return AuthVerificationRequested(
            user_id=_non_empty(payload.get("user_id", ""), "user_id"),
            email=_non_empty(payload.get("email", ""), "email"),
            ip=_validate_ip(payload.get("ip", "")),
            user_agent=_non_empty(payload.get("user_agent", ""), "user_agent"),
            geo=payload.get("geo"),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class EmailSent:
    campaign_id: str
    recipient: str
    smtp_code: int
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.campaign_id, "campaign_id")
        _non_empty(self.recipient, "recipient")
        if not isinstance(self.smtp_code, int) or self.smtp_code < 0:
            raise ValueError("smtp_code must be a non-negative integer")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "EmailSent",
            "campaign_id": self.campaign_id,
            "recipient": self.recipient,
            "smtp_code": self.smtp_code,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "EmailSent":
        payload = json.loads(data)
        return EmailSent(
            campaign_id=_non_empty(payload.get("campaign_id", ""), "campaign_id"),
            recipient=_non_empty(payload.get("recipient", ""), "recipient"),
            smtp_code=int(payload.get("smtp_code", 0)),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class EmailBounced:
    recipient: str
    bounce_type: Literal["hard", "soft", "blocked", "complaint"]
    reason: str
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.recipient, "recipient")
        _non_empty(self.reason, "reason")
        if self.bounce_type not in {"hard", "soft", "blocked", "complaint"}:
            raise ValueError("bounce_type must be one of: hard, soft, blocked, complaint")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "EmailBounced",
            "recipient": self.recipient,
            "bounce_type": self.bounce_type,
            "reason": self.reason,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "EmailBounced":
        payload = json.loads(data)
        return EmailBounced(
            recipient=_non_empty(payload.get("recipient", ""), "recipient"),
            bounce_type=payload.get("bounce_type"),
            reason=_non_empty(payload.get("reason", ""), "reason"),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class SignInSucceeded:
    user_id: str
    device_fingerprint: str
    ip: str
    mfa_used: bool
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.user_id, "user_id")
        _non_empty(self.device_fingerprint, "device_fingerprint")
        _validate_ip(self.ip)
        if not isinstance(self.mfa_used, bool):
            raise ValueError("mfa_used must be a boolean")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "SignInSucceeded",
            "user_id": self.user_id,
            "device_fingerprint": self.device_fingerprint,
            "ip": self.ip,
            "mfa_used": self.mfa_used,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "SignInSucceeded":
        payload = json.loads(data)
        return SignInSucceeded(
            user_id=_non_empty(payload.get("user_id", ""), "user_id"),
            device_fingerprint=_non_empty(payload.get("device_fingerprint", ""), "device_fingerprint"),
            ip=_validate_ip(payload.get("ip", "")),
            mfa_used=bool(payload.get("mfa_used", False)),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class SignInFailed:
    user_id: str
    device_fingerprint: Optional[str]
    ip: str
    mfa_used: bool
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.user_id, "user_id")
        if self.device_fingerprint is not None:
            _non_empty(self.device_fingerprint, "device_fingerprint")
        _validate_ip(self.ip)
        if not isinstance(self.mfa_used, bool):
            raise ValueError("mfa_used must be a boolean")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "SignInFailed",
            "user_id": self.user_id,
            "device_fingerprint": self.device_fingerprint,
            "ip": self.ip,
            "mfa_used": self.mfa_used,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "SignInFailed":
        payload = json.loads(data)
        return SignInFailed(
            user_id=_non_empty(payload.get("user_id", ""), "user_id"),
            device_fingerprint=payload.get("device_fingerprint"),
            ip=_validate_ip(payload.get("ip", "")),
            mfa_used=bool(payload.get("mfa_used", False)),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class OTProtocolFrame:
    protocol: Literal["modbus", "dnp3", "iec104", "opcua", "ethernetip"]
    src_ip: str
    dst_ip: str
    func_code: str
    addr: Optional[int]
    value: Optional[str]
    session_id: str
    timestamp: datetime

    def __post_init__(self):
        if self.protocol not in {"modbus", "dnp3", "iec104", "opcua", "ethernetip"}:
            raise ValueError("Unsupported protocol")
        _validate_ip(self.src_ip)
        _validate_ip(self.dst_ip)
        _non_empty(self.func_code, "func_code")
        _non_empty(self.session_id, "session_id")
        if self.addr is not None and (not isinstance(self.addr, int) or self.addr < 0):
            raise ValueError("addr must be a non-negative integer if provided")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "OTProtocolFrame",
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "func_code": self.func_code,
            "addr": self.addr,
            "value": self.value,
            "session_id": self.session_id,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "OTProtocolFrame":
        payload = json.loads(data)
        return OTProtocolFrame(
            protocol=payload.get("protocol"),
            src_ip=_validate_ip(payload.get("src_ip", "")),
            dst_ip=_validate_ip(payload.get("dst_ip", "")),
            func_code=_non_empty(payload.get("func_code", ""), "func_code"),
            addr=payload.get("addr"),
            value=payload.get("value"),
            session_id=_non_empty(payload.get("session_id", ""), "session_id"),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )


@dataclass(frozen=True)
class OTAssetChange:
    asset_id: str
    asset_type: Literal["plc", "rtu", "hmi", "hist", "switch", "firewall"]
    role: Literal["control", "safety", "network", "historians", "engineering"]
    ip: Optional[str]
    mac: Optional[str]
    timestamp: datetime

    def __post_init__(self):
        _non_empty(self.asset_id, "asset_id")
        if self.asset_type not in {"plc", "rtu", "hmi", "hist", "switch", "firewall"}:
            raise ValueError("asset_type must be one of: plc, rtu, hmi, hist, switch, firewall")
        if self.role not in {"control", "safety", "network", "historians", "engineering"}:
            raise ValueError("role must be one of: control, safety, network, historians, engineering")
        if self.ip is not None:
            _validate_ip(self.ip)
        if self.mac is not None:
            if not isinstance(self.mac, str) or not self.mac:
                raise ValueError("mac must be a non-empty string if provided")
        _validate_timestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "OTAssetChange",
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "role": self.role,
            "ip": self.ip,
            "mac": self.mac,
            "timestamp": _ensure_iso8601(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> "OTAssetChange":
        payload = json.loads(data)
        return OTAssetChange(
            asset_id=_non_empty(payload.get("asset_id", ""), "asset_id"),
            asset_type=payload.get("asset_type"),
            role=payload.get("role"),
            ip=payload.get("ip"),
            mac=payload.get("mac"),
            timestamp=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        )
