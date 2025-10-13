from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


class Metrics:
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, float] = {}

    def inc(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def time(self, name: str, seconds: float) -> None:
        self.timers[name] = self.timers.get(name, 0.0) + seconds


class KVStore:
    """Minimal KV abstraction (e.g., Redis) supporting windows and counters."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def _now(self) -> float:
        return time.time()

    def get(self, key: str) -> Optional[Any]:
        exp = self._expiry.get(key)
        if exp is not None and self._now() > exp:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        self._store[key] = value
        if ttl_seconds is not None:
            self._expiry[key] = self._now() + ttl_seconds

    def incr(self, key: str, ttl_seconds: Optional[int] = None, amount: int = 1) -> int:
        value = int(self.get(key) or 0) + amount
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


@dataclass
class Alert:
    severity: str
    rule: str
    message: str
    details: Dict[str, Any]


class RuleContext:
    def __init__(self, kv: KVStore, cfg: Dict[str, Any], logger: logging.Logger, alert_sink: Callable[[Alert], None], metrics: Metrics):
        self.kv = kv
        self.cfg = cfg
        self.logger = logger
        self._alert_sink = alert_sink
        self.metrics = metrics

    def alert(self, severity: str, rule: str, message: str, **details: Any) -> None:
        alert_obj = Alert(severity=severity, rule=rule, message=message, details=details)
        self._alert_sink(alert_obj)
        self.metrics.inc("alerts_fired")
