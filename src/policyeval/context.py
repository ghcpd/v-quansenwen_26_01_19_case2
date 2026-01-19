from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .utils import normalize_key


@dataclass
class EvaluationContext:
    """Context passed to rules during evaluation.

    The EvaluationContext stores the input payload, evaluation timestamp,
    strict mode, and mutable state for intermediate values and metrics.

    Attributes:
        input: The input payload being evaluated (typically a dict).
        vars: Mutable dictionary for intermediate values. Keys are normalized
            using normalize_key() (lowercase, stripped, hyphens to underscores).
        cache: Cache for memoizing expensive path lookups. Used internally
            by rules to avoid redundant deep_get calls.
        metrics: Evaluation metrics as a dict of metric_name -> count.
            Common metrics include 'rule_eval' and 'missing'.
        now: The evaluation timestamp (defaults to current UTC time).
        strict: Strict mode for handling missing data. One of:
            - 'off': Missing values return False silently
            - 'warn': Missing values return False and increment 'missing' metric
            - 'raise': Missing values raise RuleEvaluationError
    """

    input: Any
    vars: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int] = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strict: str = "warn"  # "off" | "warn" | "raise"

    def get_var(self, key: str, default: Any = None) -> Any:
        """Retrieve a variable from the context.

        Args:
            key: Variable name. Will be normalized (lowercased, stripped,
                hyphens replaced with underscores).
            default: Value to return if the variable is not set.

        Returns:
            The variable value, or default if not found.
        """
        return self.vars.get(normalize_key(key), default)

    def set_var(self, key: str, value: Any) -> None:
        """Set a variable in the context.

        Args:
            key: Variable name. Will be normalized.
            value: Value to store.
        """
        self.vars[normalize_key(key)] = value

    def bump(self, metric: str, amount: int = 1) -> None:
        """Increment a metric counter.

        Args:
            metric: Metric name. Will be normalized.
            amount: Amount to increment (default: 1).
        """
        metric = normalize_key(metric)
        self.metrics[metric] = self.metrics.get(metric, 0) + amount
