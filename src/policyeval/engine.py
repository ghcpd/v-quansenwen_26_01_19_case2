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
        return self.evaluate(policy, input_data, strict=strict, explain=True).explanation or {}
