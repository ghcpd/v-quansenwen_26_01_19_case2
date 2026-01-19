from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def deep_get(obj: Any, path: str, default: Any = None) -> Any:
    """Retrieve a nested value from an object using a dot-separated path.

    Supports traversing dicts by key and lists/tuples by integer index.
    Negative indices are supported for lists and tuples.

    Args:
        obj: The root object to traverse (typically a dict or list).
        path: Dot-separated path string (e.g., 'user.addresses.0.city').
            Empty segments are ignored.
        default: Value to return if the path cannot be resolved.

    Returns:
        The value at the specified path, or default if not found.

    Examples:
        >>> deep_get({'user': {'name': 'Alice'}}, 'user.name')
        'Alice'
        >>> deep_get({'items': [1, 2, 3]}, 'items.1')
        2
        >>> deep_get({'items': [1, 2, 3]}, 'items.-1')
        3
        >>> deep_get({}, 'missing.path', 'default')
        'default'
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
    """Normalize a string key for consistent lookup.

    Normalization includes:
        - Stripping leading/trailing whitespace
        - Converting to lowercase
        - Replacing hyphens with underscores

    Args:
        key: The key string to normalize.

    Returns:
        str: The normalized key.

    Examples:
        >>> normalize_key('  My-Key  ')
        'my_key'
        >>> normalize_key('UPPER_CASE')
        'upper_case'
    """
    return key.strip().lower().replace("-", "_")


def is_truthy(value: Any) -> bool:
    """Determine if a value is considered truthy.

    Truthy logic:
        - None: False
        - bool: The boolean value itself
        - int/float: False if 0, True otherwise
        - str: False if empty or one of '0', 'false', 'no', 'off'
          (case-insensitive, whitespace stripped); True otherwise
        - Other values: True

    Args:
        value: The value to check.

    Returns:
        bool: True if the value is truthy, False otherwise.

    Examples:
        >>> is_truthy(True)
        True
        >>> is_truthy('false')
        False
        >>> is_truthy(0)
        False
        >>> is_truthy('hello')
        True
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
