from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .errors import RuleSyntaxError, UnknownRuleError
from .rules import AllRule, AnyRule, NotRule, Rule, TruthyPathRule, parse_compare_rule

RuleFactory = Callable[[dict[str, Any], "RuleRegistry"], Rule]
"""Type alias for rule factory functions.

A rule factory takes a rule specification dict and the registry,
and returns a Rule instance.
"""


class RuleRegistry:
    """Registry mapping rule type names to factory functions.

    The registry is used by ``PolicyEngine`` to create rule instances
    from rule specification dictionaries. Custom rule types can be
    added via ``register()``.

    Example:
        >>> registry = RuleRegistry()
        >>> registry.register("custom", my_custom_factory)
        >>> rule = registry.create({"type": "custom", "field": "value"})
    """

    def __init__(self) -> None:
        """Create an empty rule registry."""
        self._factories: dict[str, RuleFactory] = {}

    def register(self, type_name: str, factory: RuleFactory) -> None:
        """Register a rule factory for a given type name.

        If a factory is already registered for the type name, it will
        be replaced.

        Args:
            type_name: The rule type identifier (e.g., ``"compare"``,
                ``"custom"``). This is the value of the ``"type"`` field
                in rule specifications.
            factory: A callable that takes a rule spec dict and the
                registry, and returns a ``Rule`` instance.
        """
        self._factories[type_name] = factory

    def unregister(self, type_name: str) -> None:
        """Remove a rule factory from the registry.

        Args:
            type_name: The rule type to remove.

        Notes:
            Does nothing if the type name is not registered.
        """
        self._factories.pop(type_name, None)

    def create(self, spec: dict[str, Any]) -> Rule:
        """Create a rule instance from a specification dictionary.

        Args:
            spec: A rule specification dict. Must have at least a
                ``"type"`` field identifying the rule type.

        Returns:
            An instantiated ``Rule`` object.

        Raises:
            RuleSyntaxError: If ``spec`` is not a dict or has no/empty
                ``"type"`` field.
            UnknownRuleError: If the rule type is not registered.
        """
        if not isinstance(spec, dict):
            raise RuleSyntaxError("rule spec must be a dict")
        type_name = spec.get("type")
        if not isinstance(type_name, str) or not type_name:
            raise RuleSyntaxError("rule spec requires non-empty 'type'")
        if type_name not in self._factories:
            raise UnknownRuleError(type_name)
        return self._factories[type_name](spec, self)


_default_registry: RuleRegistry | None = None


def get_default_registry() -> RuleRegistry:
    """Return the default rule registry with all built-in rules pre-registered.

    The default registry is lazily initialized on first access and cached
    for subsequent calls. It includes the following built-in rule types:
    ``compare``, ``all``, ``any``, ``not``, ``truthy``.

    Returns:
        The shared default ``RuleRegistry`` instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = RuleRegistry()
        register_builtin_rules(_default_registry)
    return _default_registry


def register_builtin_rules(registry: RuleRegistry) -> None:
    """Register all built-in rule types with a registry.

    This function registers the following rule types:
        - ``compare``: Compares values using operators (eq, ne, gt, etc.)
        - ``all``: Logical AND of sub-rules
        - ``any``: Logical OR of sub-rules
        - ``not``: Logical NOT of a sub-rule
        - ``truthy``: Checks if a path value is truthy

    Args:
        registry: The ``RuleRegistry`` to register rules with.
    """
    registry.register("compare", lambda spec, r: parse_compare_rule(spec))

    def _all(spec: dict[str, Any], r: RuleRegistry) -> Rule:
        items = spec.get("rules") or []
        if not isinstance(items, list):
            raise RuleSyntaxError("all rule requires list 'rules'")
        return AllRule(type_name="all", rules=[r.create(s) for s in items])

    def _any(spec: dict[str, Any], r: RuleRegistry) -> Rule:
        items = spec.get("rules") or []
        if not isinstance(items, list):
            raise RuleSyntaxError("any rule requires list 'rules'")
        return AnyRule(type_name="any", rules=[r.create(s) for s in items])

    def _not(spec: dict[str, Any], r: RuleRegistry) -> Rule:
        inner = spec.get("rule")
        if not isinstance(inner, dict):
            raise RuleSyntaxError("not rule requires dict 'rule'")
        return NotRule(type_name="not", rule=r.create(inner))

    def _truthy(spec: dict[str, Any], r: RuleRegistry) -> Rule:
        path = spec.get("path")
        if not isinstance(path, str) or not path:
            raise RuleSyntaxError("truthy rule requires non-empty 'path'")
        return TruthyPathRule(type_name="truthy", path=path)

    registry.register("all", _all)
    registry.register("any", _any)
    registry.register("not", _not)
    registry.register("truthy", _truthy)
