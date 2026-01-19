from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import PolicyLoadError, RuleSyntaxError
from .registry import RuleRegistry, get_default_registry


@dataclass(frozen=True)
class PolicySpec:
    name: str
    effect: str
    rules: list[dict[str, Any]]


def load_policy(source: Any, registry: RuleRegistry | None = None, *, base_dir: str | None = None) -> PolicySpec:
    """Load a policy from a dict, JSON string, or JSON file path."""

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
