from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .utils import normalize_key


@dataclass
class EvaluationContext:
    """Context passed to rules.

    The context stores the input payload plus evaluation-scoped variables.

    Notes:
      - `vars` is for intermediate values and can be mutated by rules.
      - `cache` is used to memoize expensive path lookups.
    """

    input: Any
    vars: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int] = field(default_factory=dict)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strict: str = "warn"  # "off" | "warn" | "raise"

    def get_var(self, key: str, default: Any = None) -> Any:
        """Read a variable using the normalized key; returns default if missing."""
        return self.vars.get(normalize_key(key), default)

    def set_var(self, key: str, value: Any) -> None:
        """Set a variable using a normalized key for consistent lookup."""
        self.vars[normalize_key(key)] = value

    def bump(self, metric: str, amount: int = 1) -> None:
        """Increment a metric counter by amount (defaults to 1)."""
        metric = normalize_key(metric)
        self.metrics[metric] = self.metrics.get(metric, 0) + amount
