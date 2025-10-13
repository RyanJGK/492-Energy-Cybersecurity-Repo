from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Tuple

from .context import RuleContext


class Rule(ABC):
    name: str = "Rule"
    priority: int = 100

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        """Evaluate event; emit alerts via context.alert when needed."""
        raise NotImplementedError


class RuleExecutor:
    def __init__(self, rules: Iterable[Rule], logger: logging.Logger | None = None):
        self.rules: List[Rule] = sorted(list(rules), key=lambda r: (r.priority, r.name))
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def execute(self, event: Dict[str, Any], context: RuleContext) -> List[Tuple[str, float, bool]]:
        """
        Execute rules against event.
        Returns list of tuples: (rule_name, latency_ms, success)
        """
        results: List[Tuple[str, float, bool]] = []
        for rule in self.rules:
            start = time.perf_counter()
            rule_name = getattr(rule, "name", rule.__class__.__name__)
            try:
                rule.evaluate(event, context)
                success = True
            except Exception as exc:  # noqa: BLE001 - rules must not break pipeline
                success = False
                self.logger.exception("Rule %s failed: %s", rule_name, exc)
            finally:
                latency_ms = (time.perf_counter() - start) * 1000.0
                context.metrics.time(f"rule_latency_ms.{rule_name}", latency_ms)
                results.append((rule_name, latency_ms, success))
        return results
