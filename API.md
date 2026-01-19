# PolicyEval API Reference

This document provides a comprehensive reference for the PolicyEval public API.

---

## Table of Contents

- [Top-level Exports](#top-level-exports)
- [Policy Loading](#policy-loading)
- [Policy Engine](#policy-engine)
- [Data Classes](#data-classes)
- [Rule Registry](#rule-registry)
- [Built-in Rule Types](#built-in-rule-types)
- [Evaluation Context](#evaluation-context)
- [Exceptions](#exceptions)
- [Utility Functions](#utility-functions)
- [Command Line Interface](#command-line-interface)

---

## Top-level Exports

```python
from policyeval import (
    Decision,
    Policy,
    PolicyEngine,
    PolicyLoadError,
    RuleEvaluationError,
    RuleRegistry,
    RuleSyntaxError,
    UnknownRuleError,
    get_default_registry,
    load_policy,
)
```

---

## Policy Loading

### `load_policy(source, registry=None, *, base_dir=None)`

Loads and validates a policy definition, returning a `PolicySpec`.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `source` | `dict`, `str`, or `pathlib.Path` | A policy as a dictionary, a JSON string, or a path to a JSON file. If a string that starts with `{`, it is parsed as inline JSON; otherwise it is treated as a file path. |
| `registry` | `RuleRegistry` or `None` | Optional registry to use for validating rule types. Defaults to the result of `get_default_registry()`. |
| `base_dir` | `str` or `None` | Optional base directory for resolving relative file paths. Only used when `source` is a relative path. |

**Returns:**

- `PolicySpec` — A frozen dataclass containing the policy's `name`, `effect`, and `rules`.

**Raises:**

- `PolicyLoadError` — If the source cannot be parsed, the JSON is invalid, the file cannot be read, or required fields are missing/invalid.
- `RuleSyntaxError` — If any rule specification in the policy is syntactically invalid.

**Example:**

```python
from policyeval import load_policy

# From a dictionary
policy = load_policy({
    "name": "admin-only",
    "effect": "allow",
    "rules": [{"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}]
})

# From a JSON string
policy = load_policy('{"name": "test", "effect": "deny", "rules": []}')

# From a file path
policy = load_policy("examples/policy.json")

# With base_dir for relative paths
policy = load_policy("policy.json", base_dir="/etc/policies")
```

---

## Policy Engine

### `class PolicyEngine`

The main entry point for evaluating policies against input payloads.

#### `PolicyEngine.__init__(registry=None, *, strict="warn")`

Creates a new policy engine.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `registry` | `RuleRegistry` or `None` | `None` | The rule registry to use for compiling rules. If `None`, uses `get_default_registry()`. |
| `strict` | `str` | `"warn"` | Default strict mode for evaluations. Must be one of `"off"`, `"warn"`, or `"raise"`. |

**Strict Mode Behavior:**

| Mode | Behavior on Missing Data |
|------|--------------------------|
| `"off"` | Missing values evaluate to `False` silently |
| `"warn"` | Missing values evaluate to `False` and increment the `missing` metric |
| `"raise"` | Raises `RuleEvaluationError` when data is missing |

**Example:**

```python
from policyeval import PolicyEngine, RuleRegistry

# With defaults
engine = PolicyEngine()

# With custom registry and strict mode
registry = RuleRegistry()
engine = PolicyEngine(registry=registry, strict="raise")
```

---

#### `PolicyEngine.compile(spec)`

Compiles a `PolicySpec` into an executable `Policy`.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `spec` | `PolicySpec` | A policy specification returned by `load_policy()`. |

**Returns:**

- `Policy` — A compiled policy with instantiated rule objects.

**Raises:**

- `UnknownRuleError` — If a rule type is not registered.
- `RuleSyntaxError` — If a rule specification is invalid.

**Example:**

```python
spec = load_policy({"name": "test", "effect": "allow", "rules": []})
engine = PolicyEngine()
compiled = engine.compile(spec)
```

---

#### `PolicyEngine.evaluate(policy, input_data, *, strict=None, now=None, explain=False)`

Evaluates a policy against input data and returns a `Decision`.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `policy` | `PolicySpec` or `Policy` | — | The policy to evaluate. Can be a `PolicySpec` (which will be compiled) or a pre-compiled `Policy`. |
| `input_data` | `Any` | — | The input payload to evaluate the policy against. Typically a dictionary. |
| `strict` | `str` or `None` | `None` | Strict mode for this evaluation. If `None`, uses the engine's default. Must be `"off"`, `"warn"`, or `"raise"`. |
| `now` | `datetime` or `None` | `None` | The current time to use for evaluation. If `None`, uses `datetime.now(timezone.utc)`. |
| `explain` | `bool` | `False` | If `True`, includes detailed explanation in the returned `Decision`. |

**Returns:**

- `Decision` — A frozen dataclass with the evaluation result containing:
  - `allowed` (`bool`): Whether the policy allows the action.
  - `policy` (`str`): The policy name.
  - `effect` (`str`): The policy effect (`"allow"` or `"deny"`).
  - `matched` (`bool`): Whether all rules matched.
  - `explanation` (`dict` or `None`): Detailed breakdown if `explain=True`.

**Decision Logic:**

| Effect | Rules Match | `allowed` Result |
|--------|-------------|------------------|
| `"allow"` | `True` | `True` |
| `"allow"` | `False` | `False` |
| `"deny"` | `True` | `False` |
| `"deny"` | `False` | `True` |

**Raises:**

- `PolicyLoadError` — If `policy` is neither a `PolicySpec` nor a `Policy`.
- `RuleEvaluationError` — If strict mode is `"raise"` and a rule fails due to missing data.

**Example:**

```python
from policyeval import PolicyEngine, load_policy

policy = load_policy({
    "name": "admin-only",
    "effect": "allow",
    "rules": [{"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}]
})

engine = PolicyEngine()
decision = engine.evaluate(policy, {"user": {"role": "admin"}})
print(decision.allowed)  # True
print(decision.matched)  # True
```

---

#### `PolicyEngine.explain(policy, input_data, *, strict=None)`

Convenience method that evaluates a policy with explanations enabled.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `policy` | `PolicySpec` or `Policy` | — | The policy to evaluate. |
| `input_data` | `Any` | — | The input payload. |
| `strict` | `str` or `None` | `None` | Strict mode override. |

**Returns:**

- `dict` — The explanation dictionary containing:
  - `matched` (`bool`): Whether all rules matched.
  - `effect` (`str`): The policy effect.
  - `metrics` (`dict`): Evaluation metrics.
  - `rules` (`list`): Per-rule evaluation details.

**Example:**

```python
explanation = engine.explain(policy, {"user": {"role": "guest"}})
print(explanation)
# {
#   "matched": False,
#   "effect": "allow",
#   "metrics": {"rule_eval": 1},
#   "rules": [{"type": "compare", "path": "user.role", ...}]
# }
```

---

## Data Classes

### `class PolicySpec`

A frozen dataclass representing a loaded (but not compiled) policy specification.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | The policy name. Must be a non-empty string. |
| `effect` | `str` | The policy effect. Must be `"allow"` or `"deny"`. |
| `rules` | `list[dict[str, Any]]` | List of rule specifications as dictionaries. |

---

### `class Policy`

A frozen dataclass representing a compiled policy with instantiated rule objects.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | The policy name. |
| `effect` | `str` | The policy effect (`"allow"` or `"deny"`). |
| `rules` | `list[Rule]` | List of compiled `Rule` objects. |

---

### `class Decision`

A frozen dataclass representing the result of a policy evaluation.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `allowed` | `bool` | Whether the policy allows the action. |
| `policy` | `str` | The name of the evaluated policy. |
| `effect` | `str` | The policy's effect (`"allow"` or `"deny"`). |
| `matched` | `bool` | Whether all rules in the policy matched. |
| `explanation` | `dict[str, Any]` or `None` | Detailed evaluation breakdown if `explain=True` was passed. |

---

## Rule Registry

### `class RuleRegistry`

Registry mapping rule type names to factory functions.

#### `RuleRegistry.__init__()`

Creates an empty rule registry.

---

#### `RuleRegistry.register(type_name, factory)`

Registers a rule factory for a given type name.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `type_name` | `str` | The rule type identifier (e.g., `"compare"`, `"custom"`). |
| `factory` | `Callable[[dict, RuleRegistry], Rule]` | A callable that takes a rule spec dictionary and the registry, returning a `Rule` instance. |

**Example:**

```python
from policyeval import RuleRegistry

def my_factory(spec, registry):
    # Parse spec and return a Rule instance
    return MyCustomRule(spec["path"])

registry = RuleRegistry()
registry.register("my_rule", my_factory)
```

---

#### `RuleRegistry.unregister(type_name)`

Removes a rule factory from the registry.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `type_name` | `str` | The rule type to remove. |

**Notes:**

- Does nothing if the type is not registered (no error raised).

---

#### `RuleRegistry.create(spec)`

Creates a rule instance from a specification dictionary.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `spec` | `dict[str, Any]` | A rule specification with at least a `"type"` key. |

**Returns:**

- `Rule` — The instantiated rule object.

**Raises:**

- `RuleSyntaxError` — If `spec` is not a dict or lacks a valid `"type"` key.
- `UnknownRuleError` — If the rule type is not registered.

---

### `get_default_registry()`

Returns the global default `RuleRegistry` with all built-in rules registered.

**Returns:**

- `RuleRegistry` — The singleton default registry.

**Notes:**

- The default registry is created lazily on first call.
- Includes built-in rules: `compare`, `all`, `any`, `not`, `truthy`.

---

## Built-in Rule Types

All rules require a `"type"` field matching the rule type name.

### `compare` Rule

Compares a value at a path against a reference value using an operator.

**Specification:**

```json
{
  "type": "compare",
  "path": "<dot.separated.path>",
  "op": "<operator>",
  "value": <any>
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | `str` | Yes | Dot-separated path to the value in input data. Supports array indexing with numeric segments. |
| `op` | `str` | Yes | Comparison operator. |
| `value` | `Any` | No | The value to compare against. Required for most operators. |

**Operators:**

| Operator | Description | Value Required |
|----------|-------------|----------------|
| `eq` | Equal to | Yes |
| `ne` | Not equal to | Yes |
| `gt` | Greater than | Yes |
| `gte` | Greater than or equal | Yes |
| `lt` | Less than | Yes |
| `lte` | Less than or equal | Yes |
| `in` | Actual value is in `value` (which should be a list) | Yes |
| `contains` | `value` is contained in actual value | Yes |
| `exists` | Value exists at path (not `None`) | No |

**Examples:**

```json
{"type": "compare", "path": "user.age", "op": "gte", "value": 18}
{"type": "compare", "path": "user.role", "op": "in", "value": ["admin", "moderator"]}
{"type": "compare", "path": "items.0.name", "op": "eq", "value": "first"}
{"type": "compare", "path": "user.verified", "op": "exists"}
```

---

### `all` Rule

Logical AND — all nested rules must match.

**Specification:**

```json
{
  "type": "all",
  "rules": [<rule>, <rule>, ...]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rules` | `list[dict]` | Yes | Array of rule specifications. |

**Behavior:**

- Returns `True` if all rules evaluate to `True`.
- Short-circuits on first `False`.
- Returns `True` for an empty `rules` list.

---

### `any` Rule

Logical OR — at least one nested rule must match.

**Specification:**

```json
{
  "type": "any",
  "rules": [<rule>, <rule>, ...]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rules` | `list[dict]` | Yes | Array of rule specifications. |

**Behavior:**

- Returns `True` if at least one rule evaluates to `True`.
- Short-circuits on first `True`.
- Returns `False` for an empty `rules` list.

---

### `not` Rule

Logical NOT — negates a single nested rule.

**Specification:**

```json
{
  "type": "not",
  "rule": <rule>
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rule` | `dict` | Yes | A single rule specification to negate. |

---

### `truthy` Rule

Checks if the value at a path is truthy.

**Specification:**

```json
{
  "type": "truthy",
  "path": "<dot.separated.path>"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | `str` | Yes | Dot-separated path to the value. |

**Truthy Logic:**

| Value | Result |
|-------|--------|
| `None` | `False` |
| `True` | `True` |
| `False` | `False` |
| `0` (int or float) | `False` |
| Non-zero numbers | `True` |
| `""`, `"0"`, `"false"`, `"no"`, `"off"` (case-insensitive, stripped) | `False` |
| Other strings | `True` |
| Other values | `True` |

---

## Evaluation Context

### `class EvaluationContext`

Context object passed to rules during evaluation. Rules may read input data and store intermediate values.

**Attributes:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `input` | `Any` | — | The input payload being evaluated. |
| `vars` | `dict[str, Any]` | `{}` | Mutable dictionary for intermediate values. Keys are normalized. |
| `cache` | `dict[str, Any]` | `{}` | Cache for memoizing expensive path lookups. |
| `metrics` | `dict[str, int]` | `{}` | Evaluation metrics (e.g., `rule_eval`, `missing`). |
| `now` | `datetime` | Current UTC time | The evaluation timestamp. |
| `strict` | `str` | `"warn"` | Strict mode (`"off"`, `"warn"`, `"raise"`). |

#### `EvaluationContext.get_var(key, default=None)`

Retrieves a variable from the context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `key` | `str` | Variable name (will be normalized). |
| `default` | `Any` | Default value if not found. |

**Returns:**

- The variable value, or `default` if not set.

---

#### `EvaluationContext.set_var(key, value)`

Sets a variable in the context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `key` | `str` | Variable name (will be normalized). |
| `value` | `Any` | Value to store. |

---

#### `EvaluationContext.bump(metric, amount=1)`

Increments a metric counter.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `metric` | `str` | Metric name (will be normalized). |
| `amount` | `int` | Amount to increment (default: 1). |

---

## Exceptions

All exceptions inherit from `PolicyEvalError`.

### `class PolicyEvalError`

Base exception for the policyeval package.

---

### `class PolicyLoadError`

Raised when a policy cannot be loaded or parsed.

**Common Causes:**

- Invalid JSON syntax
- Missing required `name` field
- Invalid `effect` value (not `"allow"` or `"deny"`)
- `rules` is not a list
- File not found or not readable
- Unsupported source type

---

### `class UnknownRuleError`

Raised when a rule type is not registered in the registry.

---

### `class RuleSyntaxError`

Raised when a rule specification is syntactically invalid.

**Common Causes:**

- Rule spec is not a dictionary
- Missing or empty `type` field
- Missing required fields for specific rule types

---

### `class RuleEvaluationError`

Raised when a rule fails during evaluation.

**Common Causes:**

- Missing value at path when strict mode is `"raise"`
- Type comparison errors
- Unknown comparison operator

---

## Utility Functions

The following utility functions are used internally and available in `policyeval.utils`:

### `deep_get(obj, path, default=None)`

Retrieves a nested value from an object using a dot-separated path.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `obj` | `Any` | The root object (typically a dict or list). |
| `path` | `str` | Dot-separated path (e.g., `"user.addresses.0.city"`). |
| `default` | `Any` | Value to return if path not found. |

**Returns:**

- The value at the path, or `default` if not found.

**Path Syntax:**

- Dots separate path segments: `"user.name"`
- Numeric segments index into lists/tuples: `"items.0.id"`
- Negative indices are supported: `"items.-1.id"`

---

### `normalize_key(key)`

Normalizes a string key for consistent lookup.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `key` | `str` | The key to normalize. |

**Returns:**

- `str` — Lowercase, stripped, with hyphens replaced by underscores.

---

### `is_truthy(value)`

Determines if a value is considered truthy.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `value` | `Any` | The value to check. |

**Returns:**

- `bool` — `True` if truthy, `False` otherwise.

See the `truthy` rule section for the truthiness logic.

---

## Command Line Interface

The CLI is invoked via:

```bash
python -m policyeval <command> [args]
```

### `evaluate` Command

Evaluates a policy against a JSON input payload.

```bash
python -m policyeval evaluate --policy <path-or-json> --input <json> [options]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--policy` | Yes | Path to a JSON policy file, or inline JSON string. |
| `--input` | Yes | Inline JSON payload to evaluate. |
| `--strict` | No | Strict mode: `off`, `warn`, or `raise`. |
| `--explain` | No | If present, outputs detailed JSON explanation. |

**Exit Codes:**

| Code | Meaning |
|------|---------|
| `0` | Policy allowed the action |
| `2` | Unknown command |
| `3` | Policy denied the action |

**Examples:**

```bash
# Evaluate from file
python -m policyeval evaluate \
  --policy examples/policy.json \
  --input '{"user":{"role":"admin"}}'

# Evaluate with inline policy and explanation
python -m policyeval evaluate \
  --policy '{"name":"test","effect":"allow","rules":[]}' \
  --input '{}' \
  --explain

# With strict mode
python -m policyeval evaluate \
  --policy examples/policy.json \
  --input '{"user":{}}' \
  --strict raise
```
