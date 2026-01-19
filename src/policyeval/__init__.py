"""PolicyEval: A configuration-driven policy evaluation engine.

PolicyEval loads policies from JSON and evaluates them against input payloads.
It provides a simple, extensible rule system for access control and policy
enforcement.

Quick Start:
    >>> from policyeval import PolicyEngine, load_policy
    >>> policy = load_policy({
    ...     "name": "admin-only",
    ...     "effect": "allow",
    ...     "rules": [{"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}]
    ... })
    >>> engine = PolicyEngine()
    >>> decision = engine.evaluate(policy, {"user": {"role": "admin"}})
    >>> decision.allowed
    True

Core Classes:
    PolicyEngine: Main entry point for evaluating policies.
    Policy: A compiled policy ready for evaluation.
    Decision: The result of policy evaluation.

Loading:
    load_policy: Load and validate policies from dict, JSON string, or file.

Registry:
    RuleRegistry: Registry for custom rule types.
    get_default_registry: Get the default registry with built-in rules.

Exceptions:
    PolicyLoadError: Policy loading or parsing failed.
    RuleEvaluationError: Rule failed during evaluation.
    RuleSyntaxError: Invalid rule specification.
    UnknownRuleError: Unknown rule type referenced.

See Also:
    API.md for comprehensive API documentation.
"""

from .engine import Decision, Policy, PolicyEngine
from .errors import (
    PolicyLoadError,
    RuleEvaluationError,
    RuleSyntaxError,
    UnknownRuleError,
)
from .loader import load_policy
from .registry import RuleRegistry, get_default_registry

__all__ = [
    "Decision",
    "Policy",
    "PolicyEngine",
    "PolicyLoadError",
    "RuleEvaluationError",
    "RuleRegistry",
    "RuleSyntaxError",
    "UnknownRuleError",
    "get_default_registry",
    "load_policy",
]
