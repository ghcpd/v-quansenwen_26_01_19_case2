from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .utils import normalize_key


@dataclass
class EvaluationContext:
    """Context passed to rules during evaluation.

    The context stores the input payload plus evaluation-scoped variables,
    cache, metrics, and configuration.

    Attributes:
        input: The input payload being evaluated (typically a dict)
        vars: Mutable variables for intermediate values (can be used by custom rules)
        cache: Memoization cache for expensive operations (e.g., path lookups)
        metrics: Evaluation metrics (e.g., 'rule_eval', 'missing')
        now: Current time for time-based evaluations
        strict: Strict mode for missing data: "off", "warn", or "raise"
    """

    input: Any
    vars: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int] = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strict: str = "warn"  # "off" | "warn" | "raise"

    def get_var(self, key: str, default: Any = None) -> Any:
        """Retrieve a variable by key.

        Args:
            key: Variable key (normalized: lowercased, hyphens to underscores)
            default: Default value if key not found

        Returns:
            Variable value or default
        """
        return self.vars.get(normalize_key(key), default)

    def set_var(self, key: str, value: Any) -> None:
        """Set a variable.

        Args:
            key: Variable key (will be normalized)
            value: Value to store
        """
        self.vars[normalize_key(key)] = value

    def bump(self, metric: str, amount: int = 1) -> None:
        """Increment a metric counter.

        Args:
            metric: Metric name (will be normalized)
            amount: Amount to increment (default: 1)
        """
        metric = normalize_key(metric)
        self.metrics[metric] = self.metrics.get(metric, 0) + amount
