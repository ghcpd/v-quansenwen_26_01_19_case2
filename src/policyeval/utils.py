from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def deep_get(obj: Any, path: str, default: Any = None) -> Any:
    """Retrieve a nested value from an object using dot-separated path notation.

    Traverses nested dicts, lists, and tuples to retrieve a value at the
    specified path. Returns the default value if any part of the path
    cannot be resolved.

    Args:
        obj: The object to traverse (typically a dict or list).
        path: Dot-separated path to the desired value. Examples:
            - ``"user.name"`` for ``{"user": {"name": "Alice"}}``
            - ``"items.0.id"`` for ``{"items": [{"id": 1}]}``
            - ``"items.-1"`` for the last element of a list
        default: Value to return if the path cannot be resolved.

    Returns:
        The value at the specified path, or ``default`` if not found.

    Path resolution rules:
        - Dict/Mapping: Keys are matched by string lookup
        - List/tuple: Segments are parsed as integers (supports negative indices)
        - Empty segments (consecutive dots) are ignored
        - Returns ``default`` if any segment fails to resolve

    Examples:
        >>> deep_get({"a": {"b": 1}}, "a.b")
        1
        >>> deep_get({"items": [10, 20]}, "items.1")
        20
        >>> deep_get({}, "missing.path", default="N/A")
        'N/A'
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
    """Normalize a key string for consistent lookups.

    Applies the following transformations:
        - Strips leading and trailing whitespace
        - Converts to lowercase
        - Replaces hyphens with underscores

    Args:
        key: The key string to normalize.

    Returns:
        The normalized key string.

    Examples:
        >>> normalize_key("  My-Key  ")
        'my_key'
        >>> normalize_key("UPPER_CASE")
        'upper_case'
    """
    return key.strip().lower().replace("-", "_")


def is_truthy(value: Any) -> bool:
    """Determine if a value is \"truthy\" according to policyeval semantics.

    This function implements custom truthiness rules that differ from
    Python's default ``bool()`` behavior, particularly for strings.

    Args:
        value: The value to check.

    Returns:
        ``True`` if the value is considered truthy, ``False`` otherwise.

    Truthiness rules:
        - ``None``: Always ``False``
        - ``bool``: The value itself
        - ``int``/``float``: ``True`` if not ``0``
        - ``str``: ``False`` if empty or (after strip/lowercase) one of:
          ``"0"``, ``"false"``, ``"no"``, ``"off"``; otherwise ``True``
        - Other types: Always ``True``

    Examples:
        >>> is_truthy(True)
        True
        >>> is_truthy("false")
        False
        >>> is_truthy("  NO  ")
        False
        >>> is_truthy("yes")
        True
        >>> is_truthy([])
        True  # Note: differs from Python's bool([])
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
