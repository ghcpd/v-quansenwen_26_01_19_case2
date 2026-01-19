from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import PolicyLoadError, RuleSyntaxError
from .registry import RuleRegistry, get_default_registry


@dataclass(frozen=True)
class PolicySpec:
    """A loaded but not yet compiled policy specification.

    PolicySpec is a frozen dataclass containing the raw policy definition
    as loaded from JSON. It is returned by load_policy() and can be passed
    to PolicyEngine.evaluate() or PolicyEngine.compile().

    Attributes:
        name: The policy name. Must be a non-empty string.
        effect: The policy effect, either 'allow' or 'deny'.
        rules: List of rule specifications as dictionaries.
            Each dict must have a 'type' key and type-specific fields.
    """

    name: str
    effect: str
    rules: list[dict[str, Any]]


def load_policy(source: Any, registry: RuleRegistry | None = None, *, base_dir: str | None = None) -> PolicySpec:
    """Load and validate a policy from a dict, JSON string, or file path.

    This function parses and validates a policy definition, ensuring all
    required fields are present and rule specifications are valid.

    Args:
        source: The policy source. Can be:
            - A dict containing the policy definition
            - A JSON string (detected if it starts with '{')
            - A file path (str or pathlib.Path) to a JSON file
        registry: Optional RuleRegistry for validating rule types.
            If None, uses get_default_registry().
        base_dir: Optional base directory for resolving relative file paths.
            Only used when source is a relative path string.

    Returns:
        PolicySpec: A frozen dataclass containing the policy's name,
            effect, and rules.

    Raises:
        PolicyLoadError: If the source cannot be parsed, the JSON is invalid,
            the file cannot be read, or required fields are missing/invalid.
        RuleSyntaxError: If any rule specification is syntactically invalid.

    Example:
        >>> policy = load_policy({"name": "test", "effect": "allow", "rules": []})
        >>> policy = load_policy("path/to/policy.json")
        >>> policy = load_policy('{"name": "inline", "effect": "deny", "rules": []}')
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
