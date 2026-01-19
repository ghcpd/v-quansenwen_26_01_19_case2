# PolicyEval API Reference

Comprehensive reference for the PolicyEval policy evaluation engine.

## Top-level Exports

```python
from policyeval import (
    # Core classes
    PolicyEngine,
    Policy,
    Decision,
    
    # Loading
    load_policy,
    
    # Registry
    RuleRegistry,
    get_default_registry,
    
    # Exceptions
    PolicyLoadError,
    RuleEvaluationError,
    RuleSyntaxError,
    UnknownRuleError,
)
```

---

## Loading Policies

### `load_policy(source, registry=None, *, base_dir=None)`

Loads and validates a policy from a dict, JSON string, or file path.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `source` | `str`, `Path`, or `dict` | Policy source. Can be: a `dict` with policy data, a JSON string (detected by leading `{`), or a file path to a JSON file. |
| `registry` | `RuleRegistry` or `None` | Optional rule registry for validating rule types. If `None`, uses the default registry. |
| `base_dir` | `str` or `None` | Base directory for resolving relative file paths. Only used when `source` is a relative path. |

**Returns:**

- `PolicySpec` — A validated policy specification containing `name`, `effect`, and `rules`.

**Raises:**

- `PolicyLoadError` — If the source cannot be loaded, parsed, or fails validation. This includes:
  - Invalid JSON syntax
  - File not found or unreadable
  - Missing or empty `name` field
  - Invalid `effect` (must be `"allow"` or `"deny"`)
  - `rules` is not a list
  - Unsupported source type

**Example:**

```python
from policyeval import load_policy

# From a dict
policy = load_policy({
    "name": "admin-only",
    "effect": "allow",
    "rules": [{"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}]
})

# From a JSON string
policy = load_policy('{"name": "test", "effect": "deny", "rules": []}')

# From a file path
policy = load_policy("policies/admin.json", base_dir="/app/config")
```

---

## PolicySpec

A frozen dataclass representing a validated policy specification.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Unique policy name. |
| `effect` | `str` | Either `"allow"` or `"deny"`. Determines the decision when all rules match. |
| `rules` | `list[dict[str, Any]]` | List of rule specification dictionaries. |

---

## Policy

A frozen dataclass representing a compiled policy ready for evaluation.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Policy name (from the spec). |
| `effect` | `str` | Either `"allow"` or `"deny"`. |
| `rules` | `list[Rule]` | Compiled rule instances. |

---

## Decision

A frozen dataclass representing the result of policy evaluation.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `allowed` | `bool` | Whether the request is allowed. |
| `policy` | `str` | Name of the evaluated policy. |
| `effect` | `str` | The policy's effect (`"allow"` or `"deny"`). |
| `matched` | `bool` | Whether all rules matched. Note: `allowed` is `matched` when effect is `"allow"`, and `not matched` when effect is `"deny"`. |
| `explanation` | `dict[str, Any]` or `None` | Detailed evaluation breakdown (only populated if `explain=True`). |

**Explanation Structure (when present):**

```python
{
    "matched": bool,           # Whether all rules matched
    "effect": str,             # Policy effect
    "metrics": dict[str, int], # Evaluation metrics (e.g., rule_eval count, missing count)
    "rules": list[dict]        # Per-rule evaluation details
}
```

---

## PolicyEngine

The main entry point for evaluating policies against input payloads.

### Constructor

```python
PolicyEngine(registry=None, *, strict="warn")
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `registry` | `RuleRegistry` or `None` | `None` | Rule registry. If `None`, uses the default registry from `get_default_registry()`. |
| `strict` | `str` | `"warn"` | Default strict mode for evaluations. See strict modes below. |

**Strict Modes:**

| Mode | Description |
|------|-------------|
| `"off"` | Silently treat missing values as `None`; rule returns `False`. |
| `"warn"` | Same as `"off"`, but increments the `"missing"` metric in the context. |
| `"raise"` | Raise `RuleEvaluationError` when a required path is missing. |

---

### `PolicyEngine.compile(spec)`

Compiles a `PolicySpec` into a `Policy` by instantiating all rule objects.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `spec` | `PolicySpec` | A validated policy specification. |

**Returns:**

- `Policy` — A compiled policy with instantiated rule objects.

---

### `PolicyEngine.evaluate(policy, input_data, *, strict=None, now=None, explain=False)`

Evaluates a policy against input data.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `policy` | `PolicySpec` or `Policy` | — | Policy to evaluate. If a `PolicySpec`, it will be compiled first. |
| `input_data` | `Any` | — | The input payload to evaluate against. Typically a dict. |
| `strict` | `str` or `None` | `None` | Strict mode override. If `None`, uses the engine's default. |
| `now` | `datetime` or `None` | `None` | Current time for time-based rules. If `None`, uses `datetime.now(timezone.utc)`. |
| `explain` | `bool` | `False` | If `True`, populates `explanation` in the returned `Decision`. |

**Returns:**

- `Decision` — The evaluation result.

**Raises:**

- `PolicyLoadError` — If `policy` is neither a `PolicySpec` nor a `Policy`.
- `RuleEvaluationError` — If a rule fails during evaluation (e.g., strict mode is `"raise"` and a path is missing).

**Evaluation Logic:**

1. Rules are evaluated in order until one fails (returns `False`) or all pass.
2. If all rules match and `effect` is `"allow"`, the decision is `allowed=True`.
3. If all rules match and `effect` is `"deny"`, the decision is `allowed=False`.
4. If any rule fails and `effect` is `"allow"`, the decision is `allowed=False`.
5. If any rule fails and `effect` is `"deny"`, the decision is `allowed=True`.

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

### `PolicyEngine.explain(policy, input_data, *, strict=None)`

Convenience method to evaluate with explanation enabled.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `policy` | `PolicySpec` or `Policy` | — | Policy to evaluate. |
| `input_data` | `Any` | — | The input payload. |
| `strict` | `str` or `None` | `None` | Strict mode override. |

**Returns:**

- `dict[str, Any]` — The explanation dictionary (empty dict if no explanation available).

**Example:**

```python
explanation = engine.explain(policy, {"user": {"role": "guest"}})
print(explanation)
# {
#     "matched": False,
#     "effect": "allow",
#     "metrics": {"rule_eval": 1},
#     "rules": [{"type": "compare", "path": "user.role", ...}]
# }
```

---

## RuleRegistry

Registry mapping rule type names to factory functions.

### Constructor

```python
RuleRegistry()
```

Creates an empty registry. Use `register()` to add rule factories.

---

### `RuleRegistry.register(type_name, factory)`

Registers a rule factory for a given type name.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `type_name` | `str` | The rule type identifier (e.g., `"compare"`, `"custom"`). |
| `factory` | `Callable[[dict, RuleRegistry], Rule]` | A callable that takes a rule spec dict and the registry, returning a `Rule` instance. |

**Example:**

```python
from policyeval import RuleRegistry

def my_factory(spec: dict, registry: RuleRegistry) -> Rule:
    return MyCustomRule(spec["field"])

registry = RuleRegistry()
registry.register("my_rule", my_factory)
```

---

### `RuleRegistry.unregister(type_name)`

Removes a rule factory from the registry.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `type_name` | `str` | The rule type to remove. |

**Notes:**

- Does nothing if the type name is not registered.

---

### `RuleRegistry.create(spec)`

Creates a rule instance from a specification dictionary.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `spec` | `dict[str, Any]` | A rule specification with at least a `"type"` field. |

**Returns:**

- `Rule` — An instantiated rule object.

**Raises:**

- `RuleSyntaxError` — If `spec` is not a dict or has no/empty `"type"` field.
- `UnknownRuleError` — If the rule type is not registered.

---

### `get_default_registry()`

Returns the default rule registry with all built-in rules pre-registered.

**Returns:**

- `RuleRegistry` — The shared default registry.

**Notes:**

- The default registry is lazily initialized on first access.
- Built-in rules: `compare`, `all`, `any`, `not`, `truthy`.

---

## Built-in Rules

### Compare Rule

Compares a value at a path against a target value using an operator.

**Specification:**

```json
{
    "type": "compare",
    "path": "<dot-separated path>",
    "op": "<operator>",
    "value": <target value>
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Must be `"compare"`. |
| `path` | `str` | Yes | Dot-separated path to the value in input (e.g., `"user.role"`, `"items.0.name"`). |
| `op` | `str` | Yes | Comparison operator (see below). |
| `value` | `Any` | No | Target value for comparison. Required for most operators. |

**Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal (`==`) | `{"op": "eq", "value": "admin"}` |
| `ne` | Not equal (`!=`) | `{"op": "ne", "value": "guest"}` |
| `gt` | Greater than (`>`) | `{"op": "gt", "value": 18}` |
| `gte` | Greater than or equal (`>=`) | `{"op": "gte", "value": 0}` |
| `lt` | Less than (`<`) | `{"op": "lt", "value": 100}` |
| `lte` | Less than or equal (`<=`) | `{"op": "lte", "value": 99}` |
| `in` | Value is in target list | `{"op": "in", "value": ["admin", "mod"]}` |
| `contains` | Target value is in actual value | `{"op": "contains", "value": "sub"}` |
| `exists` | Path exists (value is not `None`) | `{"op": "exists"}` |

**Path Syntax:**

- Use dots to traverse nested objects: `user.profile.name`
- Use numeric indices for arrays: `items.0.id`
- Returns `None` if any path segment is missing

**Behavior on Missing Values:**

- If the path resolves to `None`:
  - `exists` operator returns `False`
  - Other operators return `False` (and may increment `"missing"` metric in `"warn"` mode or raise in `"raise"` mode)

---

### All Rule

Logical AND: matches only if all sub-rules match.

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
| `type` | `str` | Yes | Must be `"all"`. |
| `rules` | `list[dict]` | Yes | List of rule specifications. |

**Behavior:**

- Evaluates rules in order.
- Short-circuits on the first `False` result.
- Returns `True` if all rules return `True`.
- Returns `True` if `rules` is empty.

---

### Any Rule

Logical OR: matches if any sub-rule matches.

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
| `type` | `str` | Yes | Must be `"any"`. |
| `rules` | `list[dict]` | Yes | List of rule specifications. |

**Behavior:**

- Evaluates rules in order.
- Short-circuits on the first `True` result.
- Returns `True` if any rule returns `True`.
- Returns `False` if `rules` is empty.

---

### Not Rule

Logical NOT: inverts the result of a sub-rule.

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
| `type` | `str` | Yes | Must be `"not"`. |
| `rule` | `dict` | Yes | A single rule specification to negate. |

---

### Truthy Rule

Checks if a value at a path is "truthy".

**Specification:**

```json
{
    "type": "truthy",
    "path": "<dot-separated path>"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Must be `"truthy"`. |
| `path` | `str` | Yes | Dot-separated path to the value. |

**Truthiness Logic:**

| Value Type | Truthy When |
|------------|-------------|
| `None` | Never (always `False`) |
| `bool` | Value is `True` |
| `int`, `float` | Value is not `0` |
| `str` | Value is not empty, `"0"`, `"false"`, `"no"`, or `"off"` (case-insensitive, whitespace-trimmed) |
| Other | Always `True` |

---

## Exceptions

### `PolicyEvalError`

Base exception for all policyeval errors. All other exceptions inherit from this.

---

### `PolicyLoadError`

Raised when a policy cannot be loaded or parsed.

**Common Causes:**

- Invalid JSON syntax
- File not found or unreadable
- Missing required fields (`name`)
- Invalid `effect` value
- `rules` is not a list
- Unsupported source type

---

### `UnknownRuleError`

Raised when a rule type is not found in the registry.

**Example:**

```python
# This raises UnknownRuleError if "custom" is not registered
load_policy({"name": "test", "effect": "allow", "rules": [{"type": "custom"}]})
```

---

### `RuleSyntaxError`

Raised when a rule specification is syntactically invalid.

**Common Causes:**

- Rule spec is not a dict
- Missing or empty `"type"` field
- Missing required fields for specific rule types (e.g., `path` for compare)

---

### `RuleEvaluationError`

Raised when a rule fails during evaluation.

**Common Causes:**

- Missing value at path when `strict="raise"`
- Type mismatch during comparison (e.g., comparing incompatible types)
- Unknown comparison operator

---

## EvaluationContext

Internal context object passed to rules during evaluation. Exposed for custom rule implementations.

**Attributes:**

| Name | Type | Description |
|------|------|-------------|
| `input` | `Any` | The input payload being evaluated. |
| `vars` | `dict[str, Any]` | Mutable storage for intermediate values. Keys are normalized. |
| `cache` | `dict[str, Any]` | Memoization cache for path lookups. |
| `metrics` | `dict[str, int]` | Counters for evaluation metrics (e.g., `"rule_eval"`, `"missing"`). |
| `now` | `datetime` | Current time (UTC) for time-based evaluations. |
| `strict` | `str` | Strict mode: `"off"`, `"warn"`, or `"raise"`. |

**Methods:**

### `get_var(key, default=None)`

Retrieves a variable by normalized key.

### `set_var(key, value)`

Sets a variable by normalized key.

### `bump(metric, amount=1)`

Increments a metric counter.

---

## Utility Functions

These are internal utilities but may be useful for custom rule implementations.

### `deep_get(obj, path, default=None)`

Retrieves a nested value from an object using dot-separated path notation.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `obj` | `Any` | The object to traverse (typically a dict or list). |
| `path` | `str` | Dot-separated path (e.g., `"user.profile.name"` or `"items.0.id"`). |
| `default` | `Any` | Value to return if path is not found. |

**Returns:**

- The value at the path, or `default` if not found.

**Path Resolution:**

- Dict keys are matched by string lookup
- List/tuple indices are parsed as integers (supports negative indices)
- Returns `default` if any segment fails

---

### `normalize_key(key)`

Normalizes a key string for consistent lookups.

**Transformations:**

- Strips leading/trailing whitespace
- Converts to lowercase
- Replaces hyphens with underscores

---

### `is_truthy(value)`

Determines if a value is "truthy" according to policyeval semantics.

**Returns:**

- `True` if the value is considered truthy (see Truthy Rule documentation).

---

## CLI Reference

### `policyeval evaluate`

Evaluates a policy against a JSON input payload.

```bash
python -m policyeval.cli evaluate --policy <policy> --input <json> [--strict <mode>] [--explain]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--policy` | Yes | Path to a policy JSON file, or inline JSON string. |
| `--input` | Yes | Inline JSON payload to evaluate. |
| `--strict` | No | Strict mode: `off`, `warn`, or `raise`. |
| `--explain` | No | Print detailed evaluation explanation as JSON. |

**Exit Codes:**

| Code | Meaning |
|------|---------|
| `0` | Policy allowed the request. |
| `2` | Unknown command or usage error. |
| `3` | Policy denied the request. |

**Examples:**

```bash
# Basic evaluation
python -m policyeval.cli evaluate \
    --policy examples/policy.json \
    --input '{"user": {"role": "admin"}}'
# Output: allow

# With explanation
python -m policyeval.cli evaluate \
    --policy '{"name":"test","effect":"allow","rules":[]}' \
    --input '{}' \
    --explain
```
