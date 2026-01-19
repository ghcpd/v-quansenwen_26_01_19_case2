from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def deep_get(obj: Any, path: str, default: Any = None) -> Any:
    """Retrieve dotted-path values from mappings/lists; returns default when missing."""
    parts = [p for p in path.split(".") if p]
    cur = obj
    for part in parts:
        if isinstance(cur, Mapping):
            if part in cur:
                cur = cur[part]
                continue
            return default
        if isinstance(cur, (list, tuple)):
            try:
                index = int(part)
            except ValueError:
                return default
            if -len(cur) <= index < len(cur):
                cur = cur[index]
                continue
            return default
        return default
    return cur


def normalize_key(key: str) -> str:
    """Normalize a key for case-insensitive lookup and metric tracking."""
    return key.strip().lower().replace("-", "_")


def is_truthy(value: Any) -> bool:
    """Coerce arbitrary values to boolean semantics used by TruthyPathRule."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return True
