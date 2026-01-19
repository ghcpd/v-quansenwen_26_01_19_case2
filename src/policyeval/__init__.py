"""PolicyEval - A configuration-driven policy evaluation engine.

PolicyEval loads policies from JSON and evaluates them against input payloads.
It provides a flexible rule system with built-in rule types and support for
custom rule registration.

Quick Start:
    >>> from policyeval import PolicyEngine, load_policy
    >>> policy = load_policy({
    ...     "name": "admin-only",
    ...     "effect": "allow",
    ...     "rules": [{"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}]
    ... })
    >>> engine = PolicyEngine()
    >>> decision = engine.evaluate(policy, {"user": {"role": "admin"}})
    >>> print(decision.allowed)
    True

Main Components:
    - PolicyEngine: Main entry point for evaluating policies
    - load_policy(): Load and validate a policy from dict, JSON string, or file
    - Decision: Result of a policy evaluation
    - RuleRegistry: Registry for custom rule types
    - get_default_registry(): Get the default registry with built-in rules

Built-in Rule Types:
    - compare: Compare values using operators (eq, ne, gt, gte, lt, lte, in, contains, exists)
    - all: Logical AND of nested rules
    - any: Logical OR of nested rules
    - not: Logical NOT of a nested rule
    - truthy: Check if a value is truthy

Exceptions:
    - PolicyLoadError: Policy loading or parsing failed
    - UnknownRuleError: Rule type not registered
    - RuleSyntaxError: Invalid rule specification
    - RuleEvaluationError: Rule failed during evaluation

For detailed API documentation, see API.md.
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
