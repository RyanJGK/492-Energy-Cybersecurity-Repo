from __future__ import annotations

import json
import logging
import signal
import time
from dataclasses import dataclass
from threading import Event
from typing import Any, Callable, Dict, Iterable, List, Optional

from .context import KVStore, Metrics, RuleContext, Alert
from .rule_engine import RuleExecutor, Rule


@dataclass
class AgentMetrics:
    events_processed: int = 0
    alerts_fired: int = 0
    rule_latencies_ms: Dict[str, float] = None  # aggregated


class EmailVerificationAgent:
    def __init__(
        self,
        consumer: Any,
        rules: Iterable[Rule],
        cfg: Dict[str, Any],
        logger: Optional[logging.Logger] = None,
        kv: Optional[KVStore] = None,
        alert_sink: Optional[Callable[[Alert], None]] = None,
    ) -> None:
        self.consumer = consumer
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.metrics = Metrics()
        self.kv = kv or KVStore()
        self.cfg = cfg
        self.alert_sink = alert_sink or (lambda alert: self.logger.warning("ALERT: %s", alert))
        self.rule_executor = RuleExecutor(rules, logger=self.logger)
        self._stop = Event()

    def _build_context(self) -> RuleContext:
        def sink(alert: Alert) -> None:
            self.alert_sink(alert)
            self.metrics.inc("alerts_fired")
        return RuleContext(kv=self.kv, cfg=self.cfg, logger=self.logger, alert_sink=sink, metrics=self.metrics)

    def _handle_signal(self, signum, frame):  # noqa: ANN001
        self.logger.info("Received signal %s; initiating graceful shutdown", signum)
        self._stop.set()

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        ctx = self._build_context()
        last_report = time.time()
        batch: List[Dict[str, Any]] = []

        while not self._stop.is_set():
            try:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    pass
                else:
                    try:
                        event = json.loads(msg.value()) if isinstance(msg.value(), (bytes, bytearray)) else msg.value()
                    except Exception:
                        event = msg.value()
                    batch.append(event)

                # Backpressure: if batch grows large, process immediately
                if len(batch) >= int(self.cfg.get("agent", {}).get("max_batch", 100)) or (time.time() - last_report) > 1.0:
                    for ev in batch:
                        start = time.perf_counter()
                        results = self.rule_executor.execute(ev, ctx)
                        self.metrics.inc("events_processed")
                        ctx.metrics.time("event_processing_ms", (time.perf_counter() - start) * 1000.0)
                    batch.clear()
                    last_report = time.time()

                # Periodic metrics report
                if int(time.time()) % 30 == 0:
                    self.logger.info("metrics: %s", self.metrics.__dict__)

            except Exception as exc:  # surface but continue
                self.logger.exception("Agent loop error: %s", exc)

        # Drain any remaining events before exit
        self.logger.info("Draining remaining events before shutdown")
        for ev in batch:
            start = time.perf_counter()
            self.rule_executor.execute(ev, ctx)
            self.metrics.inc("events_processed")
            ctx.metrics.time("event_processing_ms", (time.perf_counter() - start) * 1000.0)
        self.logger.info("Shutdown complete")
