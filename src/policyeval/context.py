from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .utils import normalize_key


@dataclass
class EvaluationContext:
    """Context passed to rules during policy evaluation.

    The context stores the input payload plus evaluation-scoped variables,
    caching, and metrics. It is created by ``PolicyEngine.evaluate()`` and
    passed to each rule's ``evaluate()`` method.

    Attributes:
        input: The input payload being evaluated (typically a dict).
        vars: Mutable storage for intermediate values. Keys are normalized
            via ``normalize_key()`` (lowercased, hyphens to underscores).
        cache: Memoization cache for expensive path lookups. Keys are
            typically prefixed (e.g., ``"path:user.role"``).
        metrics: Counters for evaluation metrics. Common keys include
            ``"rule_eval"`` (number of rule evaluations) and ``"missing"``
            (number of missing path warnings).
        now: Current time (UTC) for time-based evaluations.
        strict: Strict mode controlling behavior on missing values.
            One of ``"off"`` (silent), ``"warn"`` (increment missing metric),
            or ``"raise"`` (raise ``RuleEvaluationError``).

    Notes:
        - ``vars`` is for intermediate values and can be mutated by rules.
        - ``cache`` is used to memoize expensive path lookups.
    """

    input: Any
    vars: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int] = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strict: str = "warn"  # "off" | "warn" | "raise"

    def get_var(self, key: str, default: Any = None) -> Any:
        """Retrieve a variable by normalized key.

        Args:
            key: The variable name. Will be normalized (lowercased,
                hyphens replaced with underscores, whitespace stripped).
            default: Value to return if the key is not found.

        Returns:
            The stored value, or ``default`` if not found.
        """
        return self.vars.get(normalize_key(key), default)

    def set_var(self, key: str, value: Any) -> None:
        """Set a variable by normalized key.

        Args:
            key: The variable name. Will be normalized (lowercased,
                hyphens replaced with underscores, whitespace stripped).
            value: The value to store.
        """
        self.vars[normalize_key(key)] = value

    def bump(self, metric: str, amount: int = 1) -> None:
        """Increment a metric counter.

        Args:
            metric: The metric name. Will be normalized (lowercased,
                hyphens replaced with underscores, whitespace stripped).
            amount: The amount to increment by. Defaults to 1.
        """
        metric = normalize_key(metric)
        self.metrics[metric] = self.metrics.get(metric, 0) + amount
