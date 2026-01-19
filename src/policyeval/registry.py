from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .errors import RuleSyntaxError, UnknownRuleError
from .rules import AllRule, AnyRule, NotRule, Rule, TruthyPathRule, parse_compare_rule

RuleFactory = Callable[[dict[str, Any], "RuleRegistry"], Rule]


class RuleRegistry:
    """Registry mapping rule type names to factories."""

    def __init__(self) -> None:
        self._factories: dict[str, RuleFactory] = {}

    def register(self, type_name: str, factory: RuleFactory) -> None:
        self._factories[type_name] = factory

    def unregister(self, type_name: str) -> None:
        self._factories.pop(type_name, None)

    def create(self, spec: dict[str, Any]) -> Rule:
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
    global _default_registry
    if _default_registry is None:
        _default_registry = RuleRegistry()
        register_builtin_rules(_default_registry)
    return _default_registry


def register_builtin_rules(registry: RuleRegistry) -> None:
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
