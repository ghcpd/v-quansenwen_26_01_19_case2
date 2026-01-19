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

    """Compiled policy ready for evaluation.

    Attributes:
      name: Policy identifier from the source spec.
      effect: Either "allow" or "deny".
      rules: List of compiled rule instances produced by the registry.
    """

    name: str
    effect: str
    rules: list[Any]


@dataclass(frozen=True)
class Decision:

    """Result of evaluating a policy.

    Attributes:
      allowed: Final decision after applying the policy effect to rule results.
      policy: Policy name used during evaluation.
      effect: Policy effect that was applied ("allow" or "deny").
      matched: True when every rule evaluated to True; False once any rule failed.
      explanation: Optional structured explanation returned when ``explain=True``.
    """

    allowed: bool
    policy: str
    effect: str
    matched: bool
    explanation: dict[str, Any] | None = None


class PolicyEngine:
    """Evaluates policies against input payloads."""

    def __init__(self, registry: RuleRegistry | None = None, *, strict: str = "warn") -> None:
        self.registry = registry or get_default_registry()
        self.strict = strict

    def compile(self, spec: PolicySpec) -> Policy:
        """Compile a PolicySpec to a Policy.

        The registry is used to create concrete rule instances. Any
        RuleSyntaxError or UnknownRuleError bubbling from registry.create is
        propagated to the caller.
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

        """Evaluate a policy or compiled Policy against ``input_data``.

        Args:
          policy: A PolicySpec (compiled on the fly) or an already compiled Policy.
          input_data: Arbitrary payload passed to rules via EvaluationContext.input.
          strict: Optional strict mode override ("off", "warn", or "raise");
            defaults to the engine default.
          now: Optional datetime injected into the EvaluationContext; defaults to
            ``datetime.now(timezone.utc)``.
          explain: When True, the returned Decision.explanation contains
            per-rule details, aggregate metrics, and the matched/effect summary.

        Returns:
          Decision with ``allowed`` reflecting the policy effect: for an
          "allow" effect, allowed is True only if all rules matched; for a
          "deny" effect, allowed is False when all rules matched.

        Raises:
          PolicyLoadError: If ``policy`` is neither PolicySpec nor Policy.
          RuleEvaluationError: If a rule raises during evaluation (including
            strict="raise" missing path handling).
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
        """Shortcut for ``evaluate(..., explain=True)`` returning only the explanation."""

        return self.evaluate(policy, input_data, strict=strict, explain=True).explanation or {}
