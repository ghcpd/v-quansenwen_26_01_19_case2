from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EvaluationContext
from .errors import RuleEvaluationError, RuleSyntaxError
from .utils import deep_get, is_truthy


class Rule:
    """Base class for all rule types.

    Rules are small predicates that are compiled from a dict specification
    and evaluated against an ``EvaluationContext``. All rule types should
    inherit from this class and implement the ``evaluate()`` method.

    Attributes:
        type_name: String identifier for the rule type (e.g., ``"compare"``).

    Subclasses should implement:
        - ``evaluate(ctx)``: Returns ``True`` if the rule matches.
        - ``explain(ctx)`` (optional): Returns a dict with evaluation details.
    """

    type_name: str = "rule"

    def evaluate(self, ctx: EvaluationContext) -> bool:
        """Evaluate this rule against the given context.

        Args:
            ctx: The evaluation context containing input data and state.

        Returns:
            ``True`` if the rule matches (passes), ``False`` otherwise.

        Raises:
            NotImplementedError: If not overridden by a subclass.
        """
        raise NotImplementedError

    def explain(self, ctx: EvaluationContext) -> dict[str, Any]:
        """Return a detailed explanation of this rule's evaluation.

        Args:
            ctx: The evaluation context containing input data and state.

        Returns:
            A dict containing at least ``"type"`` and ``"result"`` keys.
            Subclasses may include additional fields.
        """
        return {"type": self.type_name, "result": self.evaluate(ctx)}


@dataclass(frozen=True)
class CompareRule(Rule):
    """Compares a value at a path to a target value using an operator.

    This is the most commonly used rule type. It retrieves a value from
    the input using a dot-separated path and compares it to a target value.

    Attributes:
        type_name: Always ``"compare"``.
        path: Dot-separated path to the value in input (e.g., ``"user.role"``).
        op: Comparison operator. One of: ``"eq"``, ``"ne"``, ``"gt"``,
            ``"gte"``, ``"lt"``, ``"lte"``, ``"in"``, ``"contains"``,
            ``"exists"``.
        value: Target value for comparison. Not required for ``"exists"``.

    Behavior on missing values:
        - ``"exists"`` operator returns ``False``
        - Other operators return ``False`` and may raise or log depending
          on strict mode
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
    """Logical NOT: inverts the result of a sub-rule.

    Attributes:
        type_name: Always ``"not"``.
        rule: The sub-rule to negate.
    """

    type_name: str
    rule: Rule

    def evaluate(self, ctx: EvaluationContext) -> bool:
        return not self.rule.evaluate(ctx)


@dataclass(frozen=True)
class AllRule(Rule):
    """Logical AND: matches only if all sub-rules match.

    Evaluates rules in order and short-circuits on the first ``False``.
    Returns ``True`` if the rules list is empty.

    Attributes:
        type_name: Always ``"all"``.
        rules: List of sub-rules to evaluate.
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
    """Logical OR: matches if any sub-rule matches.

    Evaluates rules in order and short-circuits on the first ``True``.
    Returns ``False`` if the rules list is empty.

    Attributes:
        type_name: Always ``"any"``.
        rules: List of sub-rules to evaluate.
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
    """Checks if a value at a path is "truthy".

    Truthiness is determined by ``is_truthy()``:
        - ``None``: Always ``False``
        - ``bool``: The value itself
        - ``int``/``float``: ``True`` if not ``0``
        - ``str``: ``True`` if not empty, ``"0"``, ``"false"``, ``"no"``,
          or ``"off"`` (case-insensitive)
        - Other: Always ``True``

    Attributes:
        type_name: Always ``"truthy"``.
        path: Dot-separated path to the value.
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
    """Parse a compare rule specification into a CompareRule instance.

    Args:
        spec: A rule specification dict with the following fields:
            - ``type``: Must be ``"compare"`` (not validated here)
            - ``path``: Non-empty string, dot-separated path to value
            - ``op``: Non-empty string, comparison operator
            - ``value``: Optional target value for comparison

    Returns:
        A ``CompareRule`` instance ready for evaluation.

    Raises:
        RuleSyntaxError: If ``path`` or ``op`` is missing or empty.
    """

    path = spec.get("path")
    op = spec.get("op")
    if not isinstance(path, str) or not path:
        raise RuleSyntaxError("compare rule requires non-empty 'path'")
    if not isinstance(op, str) or not op:
        raise RuleSyntaxError("compare rule requires non-empty 'op'")
    return CompareRule(type_name="compare", path=path, op=op, value=spec.get("value"))
