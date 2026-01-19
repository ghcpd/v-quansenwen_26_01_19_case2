from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def deep_get(obj: Any, path: str, default: Any = None) -> Any:
    """Retrieve a value from a nested structure using a dot-separated path.

    Args:
        obj: Object to traverse (typically dict or list)
        path: Dot-separated path (e.g., "user.profile.name")
        default: Value to return if path doesn't exist

    Returns:
        Value at path or default

    Behavior:
        - For dicts/mappings: Looks up keys
        - For lists/tuples: Converts path segment to integer index
        - Supports negative indices for sequences
        - Returns default if any segment doesn't exist
        - Empty path segments (e.g., "a..b") are ignored

    Examples:
        >>> data = {"user": {"name": "Alice", "items": [{"id": 1}]}}
        >>> deep_get(data, "user.name")
        "Alice"
        >>> deep_get(data, "user.items.0.id")
        1
        >>> deep_get(data, "user.age", default=0)
        0
    """
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
    """Normalize a string key for case-insensitive lookup.

    Args:
        key: Key to normalize

    Returns:
        Normalized key (lowercased, hyphens replaced with underscores, stripped)

    Examples:
        >>> normalize_key("User-Role")
        "user_role"
        >>> normalize_key("  ADMIN  ")
        "admin"
    """
    return key.strip().lower().replace("-", "_")


def is_truthy(value: Any) -> bool:
    """Determine if a value should be considered truthy.

    Args:
        value: Value to check

    Returns:
        Truthiness result according to policyeval rules

    Rules:
        - None: False
        - bool: as-is
        - numbers (int, float): False if 0, otherwise True
        - strings: False if empty or one of (case-insensitive):
          "", "0", "false", "no", "off", otherwise True
        - other types: True
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return True
