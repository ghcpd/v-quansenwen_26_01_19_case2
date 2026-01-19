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
    """A compiled policy.

    Policies are compiled from a `PolicySpec` plus a registry.
    """

    name: str
    effect: str
    rules: list[Any]


@dataclass(frozen=True)
class Decision:
    """The result of a policy evaluation.

    Decision is a frozen dataclass containing the outcome of evaluating
    a policy against input data.

    Attributes:
        allowed: Whether the policy allows the action. This is the primary
            result - True means the action is permitted.
        policy: The name of the evaluated policy.
        effect: The policy's effect ('allow' or 'deny').
        matched: Whether all rules in the policy matched. Note that
            'matched' and 'allowed' differ for 'deny' policies.
        explanation: Detailed evaluation breakdown if explain=True was
            passed to evaluate(). Contains 'matched', 'effect', 'metrics',
            and 'rules' keys. None if explain=False.
    """

    allowed: bool
    policy: str
    effect: str
    matched: bool
    explanation: dict[str, Any] | None = None


class PolicyEngine:
    """Evaluates policies against input payloads.

    The PolicyEngine is the main entry point for policy evaluation. It uses
    a RuleRegistry to compile rule specifications into executable Rule objects,
    then evaluates them against input data.

    Example:
        >>> engine = PolicyEngine()
        >>> policy = load_policy({"name": "test", "effect": "allow", "rules": []})
        >>> decision = engine.evaluate(policy, {"user": {"role": "admin"}})
        >>> print(decision.allowed)
        True

    Attributes:
        registry: The RuleRegistry used to create rules.
        strict: Default strict mode for evaluations ('off', 'warn', or 'raise').
    """

    def __init__(self, registry: RuleRegistry | None = None, *, strict: str = "warn") -> None:
        """Create a new policy engine.

        Args:
            registry: The rule registry to use for compiling rules.
                If None, uses get_default_registry().
            strict: Default strict mode for evaluations. Must be one of:
                - 'off': Missing values evaluate to False silently
                - 'warn': Missing values evaluate to False and increment
                    the 'missing' metric (default)
                - 'raise': Raises RuleEvaluationError when data is missing
        """
        self.registry = registry or get_default_registry()
        self.strict = strict

    def compile(self, spec: PolicySpec) -> Policy:
        """Compile a PolicySpec into an executable Policy.

        This method creates Rule instances from the spec's rule definitions
        using the engine's registry.

        Args:
            spec: A policy specification returned by load_policy().

        Returns:
            Policy: A compiled policy with instantiated Rule objects.

        Raises:
            UnknownRuleError: If a rule type is not registered.
            RuleSyntaxError: If a rule specification is invalid.
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
            policy: The policy to evaluate. Can be a PolicySpec (which will
                be compiled) or a pre-compiled Policy.
            input_data: The input payload to evaluate against. Typically a dict.
            strict: Strict mode for this evaluation. If None, uses the engine's
                default. Must be 'off', 'warn', or 'raise'.
            now: The current time for evaluation. If None, uses
                datetime.now(timezone.utc).
            explain: If True, includes detailed explanation in the returned
                Decision's explanation attribute.

        Returns:
            Decision: A frozen dataclass containing:
                - allowed: Whether the policy allows the action
                - policy: The policy name
                - effect: The policy effect ('allow' or 'deny')
                - matched: Whether all rules matched
                - explanation: Detailed breakdown if explain=True

        Raises:
            PolicyLoadError: If policy is neither a PolicySpec nor a Policy.
            RuleEvaluationError: If strict='raise' and a rule fails due to
                missing data.

        Note:
            For 'allow' policies: allowed = matched
            For 'deny' policies: allowed = not matched
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
        """Evaluate a policy and return detailed explanation.

        This is a convenience method equivalent to calling evaluate() with
        explain=True and returning the explanation dict.

        Args:
            policy: The policy to evaluate.
            input_data: The input payload.
            strict: Strict mode override.

        Returns:
            dict: The explanation containing:
                - matched: Whether all rules matched
                - effect: The policy effect
                - metrics: Evaluation metrics (e.g., rule_eval count)
                - rules: Per-rule evaluation details
        """
        return self.evaluate(policy, input_data, strict=strict, explain=True).explanation or {}
