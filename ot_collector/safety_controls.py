from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional


class KillSwitch:
    def __init__(self, check_fn: Optional[Callable[[], bool]] = None):
        self._check_fn = check_fn or (lambda: os.getenv("OT_AGENT_DISABLED") == "1")

    def enabled(self) -> bool:
        return self._check_fn()


class ReadOnlyEnforcer:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def verify(self) -> None:
        # Stub: validate that sniff NIC has no IP and interface is in promisc
        self.logger.info("Read-only enforcement verified (stub)")


class BufferingProducer:
    def __init__(self, producer, logger: Optional[logging.Logger] = None, max_buffer: int = 10000):
        self.producer = producer
        self.buffer = []
        self.max_buffer = max_buffer
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def produce(self, key: str, value: str) -> None:
        try:
            self.producer.produce(key, value)
        except Exception:
            if len(self.buffer) < self.max_buffer:
                self.buffer.append((key, value))
                self.logger.warning("Kafka unavailable; buffering message. size=%s", len(self.buffer))
            else:
                self.logger.error("Buffer full; dropping message")

    def flush(self) -> None:
        # Attempt to resend buffered messages
        remaining = []
        for key, value in self.buffer:
            try:
                self.producer.produce(key, value)
            except Exception:
                remaining.append((key, value))
        self.buffer = remaining


class AlertRamp:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.start_time = time.time()

    def severity(self, base: str) -> str:
        elapsed_days = (time.time() - self.start_time) / 86400.0
        if elapsed_days < 3:
            return "warn"
        if elapsed_days < 10:
            return base
        return base
