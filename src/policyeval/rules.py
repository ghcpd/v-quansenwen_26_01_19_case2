from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EvaluationContext
from .errors import RuleEvaluationError, RuleSyntaxError
from .utils import deep_get, is_truthy


class Rule:
    """Base rule class.

    Rules are small predicates compiled from dict specifications.
    Subclasses must implement evaluate() and may override explain().
    """

    type_name: str = "rule"

    def evaluate(self, ctx: EvaluationContext) -> bool:
        """Evaluate the rule against the evaluation context.

        Args:
            ctx: Evaluation context containing input data and state

        Returns:
            True if the rule passes, False otherwise

        Raises:
            RuleEvaluationError: If evaluation fails
        """
        raise NotImplementedError

    def explain(self, ctx: EvaluationContext) -> dict[str, Any]:
        """Generate explanation of rule evaluation.

        Args:
            ctx: Evaluation context

        Returns:
            Dict with at minimum 'type' and 'result' keys
        """
        return {"type": self.type_name, "result": self.evaluate(ctx)}


@dataclass(frozen=True)
class CompareRule(Rule):
    """Compares a value at path to an expected value using an operator.

    Supported operators: eq, ne, gt, gte, lt, lte, in, contains, exists

    Missing data behavior:
        - If path resolves to None and op is 'exists': returns False
        - If path is None and op is not 'exists':
            - strict="raise": raises RuleEvaluationError
            - strict="warn": returns False, increments 'missing' metric
            - strict="off": returns False silently

    Attributes:
        type_name: Always "compare"
        path: Dot-separated path to value in input data
        op: Comparison operator
        value: Expected value (not used by 'exists' operator)
    """

    type_name: str
    path: str
    op: str
    value: Any = None

    def evaluate(self, ctx: EvaluationContext) -> bool:
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
    """Logical negation rule.

    Returns the inverse of the nested rule's result.

    Attributes:
        type_name: Always "not"
        rule: The rule to negate
    """
    type_name: str
    rule: Rule

    def evaluate(self, ctx: EvaluationContext) -> bool:
        return not self.rule.evaluate(ctx)


@dataclass(frozen=True)
class AllRule(Rule):
    """Logical AND rule.

    Returns True only if all nested rules return True.
    Short-circuits on first False result.
    Returns True for empty rules list.

    Attributes:
        type_name: Always "all"
        rules: List of rules to evaluate
    """
    type_name: str
    rules: list[Rule]

    def evaluate(self, ctx: EvaluationContext) -> bool:
        for rule in self.rules:
            if not rule.evaluate(ctx):
                return False
        return True


@dataclass(frozen=True)
class AnyRule(Rule):
    """Logical OR rule.

    Returns True if at least one nested rule returns True.
    Short-circuits on first True result.
    Returns False for empty rules list.

    Attributes:
        type_name: Always "any"
        rules: List of rules to evaluate
    """
    type_name: str
    rules: list[Rule]

    def evaluate(self, ctx: EvaluationContext) -> bool:
        for rule in self.rules:
            if rule.evaluate(ctx):
                return True
        return False


@dataclass(frozen=True)
class TruthyPathRule(Rule):
    """Evaluates truthiness of a value at path.

    Truthiness rules:
        - None: False
        - bool: as-is
        - numbers: False if 0, otherwise True
        - strings: False if empty or one of (case-insensitive):
          "0", "false", "no", "off", otherwise True
        - other types: True

    Missing data behavior:
        - If path resolves to None:
            - strict="raise": raises RuleEvaluationError
            - strict="warn": returns False, increments 'missing' metric
            - strict="off": returns False silently

    Attributes:
        type_name: Always "truthy"
        path: Dot-separated path to value
    """

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
    """Parse a compare rule specification.

    Args:
        spec: Rule spec dict with required keys:
            - 'path': non-empty string
            - 'op': non-empty string
            - 'value': any (optional, depends on operator)

    Returns:
        CompareRule instance

    Raises:
        RuleSyntaxError: If 'path' or 'op' is missing or invalid
    """

    path = spec.get("path")
    op = spec.get("op")
    if not isinstance(path, str) or not path:
        raise RuleSyntaxError("compare rule requires non-empty 'path'")
    if not isinstance(op, str) or not op:
        raise RuleSyntaxError("compare rule requires non-empty 'op'")
    return CompareRule(type_name="compare", path=path, op=op, value=spec.get("value"))
