from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EvaluationContext
from .errors import RuleEvaluationError, RuleSyntaxError
from .utils import deep_get, is_truthy


class Rule:
    """Base class for all rule types.

    Rules are small predicates that are compiled from a dict specification.
    Each rule evaluates to True or False based on the evaluation context.

    Subclasses must implement the evaluate() method. The explain() method
    can be overridden to provide detailed evaluation information.

    Attributes:
        type_name: The rule type identifier (e.g., 'compare', 'all').
    """

    type_name: str = "rule"

    def evaluate(self, ctx: EvaluationContext) -> bool:
        """Evaluate the rule against the given context.

        Args:
            ctx: The evaluation context containing input data and state.

        Returns:
            bool: True if the rule matches, False otherwise.

        Raises:
            NotImplementedError: If not overridden by a subclass.
        """
        raise NotImplementedError

    def explain(self, ctx: EvaluationContext) -> dict[str, Any]:
        """Return a detailed explanation of this rule's evaluation.

        Args:
            ctx: The evaluation context.

        Returns:
            dict: Explanation containing at least 'type' and 'result' keys.
                Subclasses may include additional details.
        """
        return {"type": self.type_name, "result": self.evaluate(ctx)}


@dataclass(frozen=True)
class CompareRule(Rule):
    """Compares a value at a path to a reference value using an operator.

    Supported operators:
        - eq: Equal to
        - ne: Not equal to
        - gt: Greater than
        - gte: Greater than or equal to
        - lt: Less than
        - lte: Less than or equal to
        - in: Actual value is in the reference list
        - contains: Reference value is in the actual value
        - exists: Value exists at path (is not None)

    Attributes:
        type_name: Always 'compare'.
        path: Dot-separated path to the value in input data.
        op: The comparison operator.
        value: The reference value to compare against.

    Note:
        If the value at path is None and the operator is not 'exists',
        the behavior depends on strict mode:
        - 'off': Returns False silently
        - 'warn': Returns False and increments 'missing' metric
        - 'raise': Raises RuleEvaluationError
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
    """Logical NOT rule that negates a nested rule.

    Attributes:
        type_name: Always 'not'.
        rule: The nested rule to negate.
    """
    type_name: str
    rule: Rule

    def evaluate(self, ctx: EvaluationContext) -> bool:
        return not self.rule.evaluate(ctx)


@dataclass(frozen=True)
class AllRule(Rule):
    """Logical AND rule requiring all nested rules to match.

    Evaluates nested rules in order and short-circuits on first False.
    Returns True for an empty rules list.

    Attributes:
        type_name: Always 'all'.
        rules: List of nested Rule objects.
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
    """Logical OR rule requiring at least one nested rule to match.

    Evaluates nested rules in order and short-circuits on first True.
    Returns False for an empty rules list.

    Attributes:
        type_name: Always 'any'.
        rules: List of nested Rule objects.
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
    """Rule that checks if a value at a path is truthy.

    Truthy logic:
        - None: False
        - bool: The boolean value itself
        - int/float: False if 0, True otherwise
        - str: False if empty or '0', 'false', 'no', 'off' (case-insensitive,
          stripped); True otherwise
        - Other values: True

    Attributes:
        type_name: Always 'truthy'.
        path: Dot-separated path to the value in input data.

    Note:
        If the value at path is None, behavior depends on strict mode
        (same as CompareRule).
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
    """Parse a compare rule specification dict into a CompareRule.

    Args:
        spec: A dict containing:
            - path (str, required): Dot-separated path to the value
            - op (str, required): Comparison operator
            - value (any, optional): Reference value for comparison

    Returns:
        CompareRule: The parsed rule instance.

    Raises:
        RuleSyntaxError: If 'path' or 'op' is missing or empty.
    """

    path = spec.get("path")
    op = spec.get("op")
    if not isinstance(path, str) or not path:
        raise RuleSyntaxError("compare rule requires non-empty 'path'")
    if not isinstance(op, str) or not op:
        raise RuleSyntaxError("compare rule requires non-empty 'op'")
    return CompareRule(type_name="compare", path=path, op=op, value=spec.get("value"))
