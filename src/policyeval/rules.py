from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EvaluationContext
from .errors import RuleEvaluationError, RuleSyntaxError
from .utils import deep_get, is_truthy


class Rule:
    """Base rule.

    Rules are small predicates that are compiled from a dict spec.

    Subclasses should implement `evaluate`.
    """

    type_name: str = "rule"

    def evaluate(self, ctx: EvaluationContext) -> bool:
        """Evaluate the rule against the given context."""
        raise NotImplementedError

    def explain(self, ctx: EvaluationContext) -> dict[str, Any]:
        """Return a structured explanation; by default reuses ``evaluate``."""
        return {"type": self.type_name, "result": self.evaluate(ctx)}


@dataclass(frozen=True)
class CompareRule(Rule):
    """Compares a value at `path` to `value` using `op`."""

    type_name: str
    path: str
    op: str
    value: Any = None

    def evaluate(self, ctx: EvaluationContext) -> bool:
        """Evaluate comparison and handle strict missing-value behavior.

        Raises:
          RuleEvaluationError: If strict mode is "raise" and a path is missing,
            or when an underlying comparison operation fails.
        """
        ctx.bump("rule_eval")
        cache_key = f"path:{self.path}"
        if cache_key in ctx.cache:
            actual = ctx.cache[cache_key]
        else:
            actual = deep_get(ctx.input, self.path, default=None)
            ctx.cache[cache_key] = actual

        if actual is None:
            if self.op == "exists":
                return False
            if ctx.strict == "raise":
                raise RuleEvaluationError(f"Missing value at path '{self.path}'")
            if ctx.strict == "warn":
                ctx.bump("missing")
            return False

        try:
            if self.op == "eq":
                return actual == self.value
            if self.op == "ne":
                return actual != self.value
            if self.op == "gt":
                return actual > self.value
            if self.op == "gte":
                return actual >= self.value
            if self.op == "lt":
                return actual < self.value
            if self.op == "lte":
                return actual <= self.value
            if self.op == "in":
                return actual in (self.value or [])
            if self.op == "contains":
                return self.value in actual
            if self.op == "exists":
                return True
        except Exception as exc:  # noqa: BLE001
            raise RuleEvaluationError(str(exc)) from exc

        raise RuleEvaluationError(f"Unknown compare op '{self.op}'")

    def explain(self, ctx: EvaluationContext) -> dict[str, Any]:
        """Return comparison inputs, actual value, and result."""
        actual = deep_get(ctx.input, self.path, default=None)
        return {
            "type": "compare",
            "path": self.path,
            "op": self.op,
            "value": self.value,
            "actual": actual,
            "result": self.evaluate(ctx),
        }


@dataclass(frozen=True)
class NotRule(Rule):
    """Logical negation of a single rule."""

    type_name: str
    rule: Rule

    def evaluate(self, ctx: EvaluationContext) -> bool:
        return not self.rule.evaluate(ctx)


@dataclass(frozen=True)
class AllRule(Rule):
    """Logical AND over a list of rules (fails fast)."""

    type_name: str
    rules: list[Rule]

    def evaluate(self, ctx: EvaluationContext) -> bool:
        for rule in self.rules:
            if not rule.evaluate(ctx):
                return False
        return True


@dataclass(frozen=True)
class AnyRule(Rule):
    """Logical OR over a list of rules (succeeds fast)."""

    type_name: str
    rules: list[Rule]

    def evaluate(self, ctx: EvaluationContext) -> bool:
        for rule in self.rules:
            if rule.evaluate(ctx):
                return True
        return False


@dataclass(frozen=True)
class TruthyPathRule(Rule):
    """Treats a value at path as a boolean."""

    type_name: str
    path: str

    def evaluate(self, ctx: EvaluationContext) -> bool:
        val = deep_get(ctx.input, self.path, default=None)
        if val is None:
            if ctx.strict == "raise":
                raise RuleEvaluationError(f"Missing value at path '{self.path}'")
            if ctx.strict == "warn":
                ctx.bump("missing")
            return False
        return is_truthy(val)


def parse_compare_rule(spec: dict[str, Any]) -> CompareRule:
        """Parse a compare rule spec.

        Raises:
            RuleSyntaxError: If required fields are missing or empty.
        """

    path = spec.get("path")
    op = spec.get("op")
    if not isinstance(path, str) or not path:
        raise RuleSyntaxError("compare rule requires non-empty 'path'")
    if not isinstance(op, str) or not op:
        raise RuleSyntaxError("compare rule requires non-empty 'op'")
    return CompareRule(type_name="compare", path=path, op=op, value=spec.get("value"))
