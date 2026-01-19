from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .context import EvaluationContext
from .errors import PolicyLoadError
from .loader import PolicySpec
from .registry import RuleRegistry, get_default_registry


@dataclass(frozen=True)
class Policy:
    """A compiled policy ready for evaluation.

    Policies are compiled from a `PolicySpec` plus a registry. Each rule
    in the spec is instantiated into a Rule object.

    Attributes:
        name: Policy identifier
        effect: Either "allow" or "deny"
        rules: List of compiled rule objects
    """

    name: str
    effect: str
    rules: list[Any]


@dataclass(frozen=True)
class Decision:
    """Result of a policy evaluation.

    Attributes:
        allowed: Whether the action is allowed
        policy: Name of the evaluated policy
        effect: Policy effect ("allow" or "deny")
        matched: Whether all rules in the policy matched
        explanation: Detailed evaluation info if explain=True, otherwise None
    """
    allowed: bool
    policy: str
    effect: str
    matched: bool
    explanation: dict[str, Any] | None = None


class PolicyEngine:
    """Evaluates policies against input payloads.

    The engine compiles policy specifications and evaluates them against
    input data using a configurable rule registry.
    """

    def __init__(self, registry: RuleRegistry | None = None, *, strict: str = "warn") -> None:
        """Initialize the policy engine.

        Args:
            registry: Custom rule registry. If None, uses default registry
                with all built-in rules.
            strict: Default strict mode for evaluations. Valid values:
                "off" - Silently treat missing data as False
                "warn" - Count missing data in metrics but treat as False
                "raise" - Raise RuleEvaluationError on missing data
                Default: "warn"
        """
        self.registry = registry or get_default_registry()
        self.strict = strict

    def compile(self, spec: PolicySpec) -> Policy:
        """Compile a PolicySpec into a Policy.

        Args:
            spec: The policy specification to compile

        Returns:
            A compiled Policy with instantiated rule objects

        Raises:
            UnknownRuleError: If any rule type is not registered
            RuleSyntaxError: If any rule spec is invalid
        """
        compiled = [self.registry.create(s) for s in spec.rules]
        return Policy(name=spec.name, effect=spec.effect, rules=compiled)

    def evaluate(
        self,
        policy: PolicySpec | Policy,
        input_data: Any,
        *,
        strict: str | None = None,
        now: datetime | None = None,
        explain: bool = False,
    ) -> Decision:
        """Evaluate a policy against input data.

        Args:
            policy: Policy to evaluate. If PolicySpec, will be compiled first.
            input_data: The input payload to evaluate (typically a dict)
            strict: Override engine's strict mode. Values: "off", "warn", "raise".
                If None, uses engine's default.
            now: Current time for time-based rules. If None, uses datetime.now(UTC).
            explain: If True, include detailed explanation in result. Default: False.

        Returns:
            Decision object with evaluation result and optional explanation.

        Raises:
            PolicyLoadError: If policy is not a PolicySpec or Policy
            RuleEvaluationError: If strict="raise" and data is missing

        Behavior:
            - For effect="allow": allowed = matched
            - For effect="deny": allowed = not matched
            - Rules evaluated sequentially; stops at first False result
            - If explain=True, explanation includes metrics and per-rule details
        """
        if now is None:
            now = datetime.now(timezone.utc)
        strict_mode = strict or self.strict

        if isinstance(policy, PolicySpec):
            compiled = self.compile(policy)
        elif isinstance(policy, Policy):
            compiled = policy
        else:
            raise PolicyLoadError("policy must be a PolicySpec or Policy")

        ctx = EvaluationContext(input=input_data, now=now, strict=strict_mode)

        matched = True
        details: list[dict[str, Any]] = []
        for rule in compiled.rules:
            res = rule.evaluate(ctx)
            if explain:
                details.append(rule.explain(ctx))
            if not res:
                matched = False
                break

        allowed = matched if compiled.effect == "allow" else (not matched)
        explanation = None
        if explain:
            explanation = {
                "matched": matched,
                "effect": compiled.effect,
                "metrics": dict(ctx.metrics),
                "rules": details,
            }

        return Decision(
            allowed=allowed,
            policy=compiled.name,
            effect=compiled.effect,
            matched=matched,
            explanation=explanation,
        )

    def explain(self, policy: PolicySpec | Policy, input_data: Any, *, strict: str | None = None) -> dict[str, Any]:
        """Evaluate a policy and return only the explanation.

        Convenience method that calls evaluate() with explain=True.

        Args:
            policy: Policy to evaluate
            input_data: Input payload
            strict: Strict mode override

        Returns:
            Explanation dict containing matched status, effect, metrics,
            and per-rule evaluation details.
        """
        return self.evaluate(policy, input_data, strict=strict, explain=True).explanation or {}
