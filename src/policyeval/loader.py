from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import PolicyLoadError, RuleSyntaxError
from .registry import RuleRegistry, get_default_registry


@dataclass(frozen=True)
class PolicySpec:
    """A validated policy specification.

    This is a frozen (immutable) dataclass representing a policy that has
    been loaded and validated but not yet compiled into executable rules.

    Attributes:
        name: Unique policy name. Must be a non-empty string.
        effect: Either ``"allow"`` or ``"deny"``. Determines the decision
            when all rules match: ``"allow"`` means grant access if matched,
            ``"deny"`` means deny access if matched.
        rules: List of rule specification dictionaries. Each dict must have
            at least a ``"type"`` field identifying the rule type.
    """

    name: str
    effect: str
    rules: list[dict[str, Any]]


def load_policy(source: Any, registry: RuleRegistry | None = None, *, base_dir: str | None = None) -> PolicySpec:
    """Load and validate a policy from a dict, JSON string, or file path.

    This function accepts multiple source formats and performs validation
    including checking that all referenced rule types are registered.

    Args:
        source: Policy source. Can be:
            - A ``dict`` with policy data (keys: ``name``, ``effect``, ``rules``)
            - A JSON string (detected by leading ``{`` after stripping whitespace)
            - A file path (``str`` or ``Path``) to a JSON file
        registry: Optional rule registry for validating rule types. If
            ``None``, uses the default registry from ``get_default_registry()``.
        base_dir: Base directory for resolving relative file paths. Only
            used when ``source`` is a relative path string.

    Returns:
        A validated ``PolicySpec`` containing the policy name, effect, and
        list of rule specification dicts.

    Raises:
        PolicyLoadError: If the source cannot be loaded, parsed, or fails
            validation. Wraps underlying ``json.JSONDecodeError``,
            ``OSError``, or ``RuleSyntaxError`` exceptions.

    Examples:
        >>> load_policy({"name": "test", "effect": "allow", "rules": []})
        PolicySpec(name='test', effect='allow', rules=[])

        >>> load_policy('{"name": "test", "effect": "deny", "rules": []}')
        PolicySpec(name='test', effect='deny', rules=[])

        >>> load_policy("policies/admin.json", base_dir="/app/config")
        PolicySpec(...)
    """

    registry = registry or get_default_registry()
    try:
        if isinstance(source, (str, Path)):
            text = str(source)
            if text.strip().startswith("{"):
                data = json.loads(text)
            else:
                path = Path(text)
                if not path.is_absolute() and base_dir:
                    path = Path(base_dir) / path
                data = json.loads(path.read_text(encoding="utf-8"))
        elif isinstance(source, dict):
            data = source
        else:
            raise PolicyLoadError(f"Unsupported policy source type: {type(source).__name__}")

        name = data.get("name")
        effect = data.get("effect", "allow")
        rules = data.get("rules") or []

        if not isinstance(name, str) or not name:
            raise PolicyLoadError("policy requires non-empty 'name'")
        if effect not in {"allow", "deny"}:
            raise PolicyLoadError("policy 'effect' must be 'allow' or 'deny'")
        if not isinstance(rules, list):
            raise PolicyLoadError("policy 'rules' must be a list")

        # Validate rule specs early by compiling once.
        for spec in rules:
            if not isinstance(spec, dict):
                raise RuleSyntaxError("rule spec must be a dict")
            registry.create(spec)

        return PolicySpec(name=name, effect=effect, rules=rules)
    except (json.JSONDecodeError, OSError, RuleSyntaxError) as exc:
        raise PolicyLoadError(str(exc)) from exc
