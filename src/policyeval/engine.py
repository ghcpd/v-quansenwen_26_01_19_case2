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

    Policies are compiled from a ``PolicySpec`` by instantiating all rule
    objects using the configured ``RuleRegistry``. This is a frozen
    (immutable) dataclass.

    Attributes:
        name: Policy name (from the original spec).
        effect: Either ``"allow"`` or ``"deny"``. Determines the decision
            when all rules match.
        rules: List of compiled ``Rule`` instances ready for evaluation.
    """

    name: str
    effect: str
    rules: list[Any]


@dataclass(frozen=True)
class Decision:
    """The result of policy evaluation.

    This is a frozen (immutable) dataclass returned by
    ``PolicyEngine.evaluate()``.

    Attributes:
        allowed: Whether the request is allowed. This is the final decision
            taking into account the policy effect:
            - If ``effect="allow"`` and all rules match: ``allowed=True``
            - If ``effect="allow"`` and any rule fails: ``allowed=False``
            - If ``effect="deny"`` and all rules match: ``allowed=False``
            - If ``effect="deny"`` and any rule fails: ``allowed=True``
        policy: Name of the evaluated policy.
        effect: The policy's effect (``"allow"`` or ``"deny"``).
        matched: Whether all rules in the policy matched (returned ``True``).
            Note that ``matched=True`` with ``effect="deny"`` means
            ``allowed=False``.
        explanation: Detailed evaluation breakdown. Only populated when
            ``explain=True`` was passed to ``evaluate()``. Structure:
            ``{"matched": bool, "effect": str, "metrics": dict, "rules": list}``
    """

    allowed: bool
    policy: str
    effect: str
    matched: bool
    explanation: dict[str, Any] | None = None


class PolicyEngine:
    """Evaluates policies against input payloads.

    The engine is the main entry point for policy evaluation. It handles
    compiling policy specifications into executable rules and evaluating
    them against input data.

    Attributes:
        registry: The ``RuleRegistry`` used for creating rule instances.
        strict: Default strict mode for evaluations.

    Example:
        >>> from policyeval import PolicyEngine, load_policy
        >>> policy = load_policy({"name": "test", "effect": "allow", "rules": []})
        >>> engine = PolicyEngine()
        >>> decision = engine.evaluate(policy, {})
        >>> decision.allowed
        True
    """

    def __init__(self, registry: RuleRegistry | None = None, *, strict: str = "warn") -> None:
        """Initialize a policy engine.

        Args:
            registry: Rule registry for creating rule instances. If ``None``,
                uses the default registry from ``get_default_registry()``.
            strict: Default strict mode for evaluations. One of:
                - ``"off"``: Silently treat missing values as ``None``
                - ``"warn"``: Same as "off", but increment "missing" metric
                - ``"raise"``: Raise ``RuleEvaluationError`` on missing values
        """
        self.registry = registry or get_default_registry()
        self.strict = strict

    def compile(self, spec: PolicySpec) -> Policy:
        """Compile a policy specification into an executable policy.

        Args:
            spec: A validated ``PolicySpec`` to compile.

        Returns:
            A ``Policy`` with instantiated rule objects ready for evaluation.
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
            policy: Policy to evaluate. Can be a ``PolicySpec`` (which will
                be compiled first) or a pre-compiled ``Policy``.
            input_data: The input payload to evaluate against. Typically a
                dict with nested data that rules will inspect.
            strict: Strict mode override. If ``None``, uses the engine's
                default strict mode.
            now: Current time for time-based rules. If ``None``, uses
                ``datetime.now(timezone.utc)``.
            explain: If ``True``, populates the ``explanation`` field in
                the returned ``Decision`` with detailed evaluation info.

        Returns:
            A ``Decision`` containing the evaluation result.

        Raises:
            PolicyLoadError: If ``policy`` is neither a ``PolicySpec`` nor
                a ``Policy``.
            RuleEvaluationError: If a rule fails during evaluation (e.g.,
                strict mode is ``"raise"`` and a path is missing).
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
        """Convenience method to evaluate with explanation enabled.

        This is equivalent to calling ``evaluate()`` with ``explain=True``
        and extracting the ``explanation`` field.

        Args:
            policy: Policy to evaluate. Can be a ``PolicySpec`` or ``Policy``.
            input_data: The input payload to evaluate against.
            strict: Strict mode override. If ``None``, uses the engine's
                default strict mode.

        Returns:
            The explanation dictionary containing evaluation details:
            ``{"matched": bool, "effect": str, "metrics": dict, "rules": list}``.
            Returns an empty dict if no explanation is available.
        """
        return self.evaluate(policy, input_data, strict=strict, explain=True).explanation or {}
