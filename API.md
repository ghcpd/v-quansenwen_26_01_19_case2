# PolicyEval API Reference

Comprehensive API documentation for PolicyEval, a lightweight policy evaluation engine.

## Table of Contents

- [Top-level Exports](#top-level-exports)
- [Core Classes](#core-classes)
  - [PolicyEngine](#policyengine)
  - [Policy](#policy)
  - [PolicySpec](#policyspec)
  - [Decision](#decision)
  - [RuleRegistry](#ruleregistry)
  - [EvaluationContext](#evaluationcontext)
- [Functions](#functions)
  - [load_policy](#load_policy)
  - [get_default_registry](#get_default_registry)
- [Built-in Rules](#built-in-rules)
- [Exception Classes](#exception-classes)
- [Utility Functions](#utility-functions)

---

## Top-level Exports

```python
from policyeval import (
    PolicyEngine,
    Policy,
    Decision,
    PolicySpec,  # via load_policy return type
    RuleRegistry,
    load_policy,
    get_default_registry,
    # Exception classes
    PolicyEvalError,
    PolicyLoadError,
    UnknownRuleError,
    RuleSyntaxError,
    RuleEvaluationError,
)
```

---

## Core Classes

### PolicyEngine

The main entry point for evaluating policies against input data.

#### Constructor

```python
PolicyEngine(registry=None, *, strict="warn")
```

**Parameters:**
- `registry` (`RuleRegistry | None`): Custom rule registry. If `None`, uses the default registry with all built-in rules.
- `strict` (`str`): Default strict mode for evaluations. Valid values:
  - `"off"`: Silently treat missing data as `False`
  - `"warn"`: Count missing data in metrics but treat as `False`
  - `"raise"`: Raise `RuleEvaluationError` on missing data
  
  Default: `"warn"`

**Example:**
```python
engine = PolicyEngine()
# or with custom registry
custom_registry = RuleRegistry()
engine = PolicyEngine(registry=custom_registry, strict="raise")
```

#### Methods

##### `compile(spec)`

Compiles a `PolicySpec` into a `Policy` by instantiating all rule objects.

**Parameters:**
- `spec` (`PolicySpec`): The policy specification to compile

**Returns:**
- `Policy`: A compiled policy ready for evaluation

**Example:**
```python
spec = load_policy({"name": "test", "effect": "allow", "rules": []})
policy = engine.compile(spec)
```

##### `evaluate(policy, input_data, *, strict=None, now=None, explain=False)`

Evaluates a policy against input data.

**Parameters:**
- `policy` (`PolicySpec | Policy`): Policy to evaluate. If `PolicySpec`, it will be compiled first.
- `input_data` (`Any`): The input payload to evaluate against. Typically a dict.
- `strict` (`str | None`): Override the engine's default strict mode for this evaluation. Values: `"off"`, `"warn"`, `"raise"`. If `None`, uses the engine's default.
- `now` (`datetime | None`): Current time for time-based rules. If `None`, uses `datetime.now(timezone.utc)`.
- `explain` (`bool`): If `True`, includes detailed explanation in the returned `Decision`. Default: `False`.

**Returns:**
- `Decision`: Result object containing:
  - `allowed` (`bool`): Whether the request is allowed
  - `policy` (`str`): Name of the evaluated policy
  - `effect` (`str`): Policy effect (`"allow"` or `"deny"`)
  - `matched` (`bool`): Whether all rules matched
  - `explanation` (`dict | None`): Detailed evaluation info if `explain=True`

**Raises:**
- `PolicyLoadError`: If policy is not a `PolicySpec` or `Policy`
- `RuleEvaluationError`: If strict mode is `"raise"` and data is missing

**Behavior:**
- For `effect="allow"`: `allowed = matched`
- For `effect="deny"`: `allowed = not matched`
- Rules are evaluated sequentially; evaluation stops at first `False` result
- If `explain=True`, all rules are evaluated and results included in explanation

**Example:**
```python
policy = load_policy({"name": "admin_only", "effect": "allow", "rules": [
    {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}
]})
decision = engine.evaluate(policy, {"user": {"role": "admin"}})
print(decision.allowed)  # True
```

##### `explain(policy, input_data, *, strict=None)`

Convenience method that calls `evaluate()` with `explain=True` and returns only the explanation.

**Parameters:**
- Same as `evaluate()` except `explain` parameter is implicit

**Returns:**
- `dict[str, Any]`: Explanation dictionary containing:
  - `matched` (`bool`): Whether all rules matched
  - `effect` (`str`): Policy effect
  - `metrics` (`dict[str, int]`): Evaluation metrics
  - `rules` (`list[dict]`): Per-rule evaluation details

**Example:**
```python
explanation = engine.explain(policy, {"user": {"role": "guest"}})
print(explanation["matched"])  # False
```

---

### Policy

A compiled policy ready for evaluation. Immutable.

**Fields:**
- `name` (`str`): Policy name
- `effect` (`str`): Either `"allow"` or `"deny"`
- `rules` (`list[Any]`): List of compiled rule objects

**Note:** `Policy` objects are created by `PolicyEngine.compile()` or internally during `evaluate()`. Users typically don't instantiate these directly.

---

### PolicySpec

A loaded policy specification before compilation. Immutable.

**Fields:**
- `name` (`str`): Policy name
- `effect` (`str`): Either `"allow"` or `"deny"`
- `rules` (`list[dict[str, Any]]`): List of rule specifications (dicts)

**Note:** `PolicySpec` objects are created by `load_policy()`. Users typically don't instantiate these directly.

---

### Decision

Result of a policy evaluation. Immutable.

**Fields:**
- `allowed` (`bool`): Whether the action is allowed
- `policy` (`str`): Name of the policy that was evaluated
- `effect` (`str`): Policy effect (`"allow"` or `"deny"`)
- `matched` (`bool`): Whether all rules in the policy matched
- `explanation` (`dict[str, Any] | None`): Detailed explanation if requested, otherwise `None`

**Explanation Structure** (when `explain=True`):
```python
{
    "matched": bool,
    "effect": str,
    "metrics": {
        "rule_eval": int,      # Number of rule evaluations
        "missing": int,        # Number of missing path warnings
        # ... other metrics
    },
    "rules": [
        {
            "type": str,       # Rule type
            "result": bool,    # Rule result
            # ... rule-specific fields
        },
        # ... one entry per rule
    ]
}
```

---

### RuleRegistry

Registry that maps rule type names to factory functions.

#### Constructor

```python
RuleRegistry()
```

Creates an empty registry. To get a pre-populated registry with built-in rules, use `get_default_registry()`.

#### Methods

##### `register(type_name, factory)`

Registers a rule factory for a given type name.

**Parameters:**
- `type_name` (`str`): The rule type identifier (e.g., `"compare"`)
- `factory` (`Callable[[dict[str, Any], RuleRegistry], Rule]`): Factory function that takes a rule spec dict and the registry, and returns a `Rule` instance

**Example:**
```python
def my_rule_factory(spec, registry):
    return MyCustomRule(data=spec.get("data"))

registry = RuleRegistry()
registry.register("my_rule", my_rule_factory)
```

##### `unregister(type_name)`

Removes a rule type from the registry.

**Parameters:**
- `type_name` (`str`): The rule type to remove

**Note:** If the type is not registered, this method does nothing (no error).

##### `create(spec)`

Creates a rule instance from a specification dict.

**Parameters:**
- `spec` (`dict[str, Any]`): Rule specification containing at minimum a `"type"` key

**Returns:**
- `Rule`: An instance of the appropriate rule class

**Raises:**
- `RuleSyntaxError`: If spec is not a dict or missing/invalid `"type"`
- `UnknownRuleError`: If the rule type is not registered

**Example:**
```python
rule = registry.create({"type": "compare", "path": "user.id", "op": "eq", "value": 123})
```

---

### EvaluationContext

Context object passed to rules during evaluation. Contains input data, variables, cache, and metrics.

**Fields:**
- `input` (`Any`): The input payload being evaluated
- `vars` (`dict[str, Any]`): Mutable variables for intermediate values (can be used by custom rules)
- `cache` (`dict[str, Any]`): Memoization cache for expensive operations (e.g., path lookups)
- `metrics` (`dict[str, int]`): Evaluation metrics (e.g., `"rule_eval"`, `"missing"`)
- `now` (`datetime`): Current time for time-based evaluations
- `strict` (`str`): Strict mode for this evaluation (`"off"`, `"warn"`, or `"raise"`)

**Methods:**

##### `get_var(key, default=None)`

Retrieves a variable by key (case-insensitive, normalized).

**Parameters:**
- `key` (`str`): Variable key
- `default` (`Any`): Default value if key not found

**Returns:**
- `Any`: Variable value or default

##### `set_var(key, value)`

Sets a variable (key is normalized: lowercased, hyphens converted to underscores).

**Parameters:**
- `key` (`str`): Variable key
- `value` (`Any`): Value to store

##### `bump(metric, amount=1)`

Increments a metric counter.

**Parameters:**
- `metric` (`str`): Metric name (normalized)
- `amount` (`int`): Amount to increment (default: 1)

**Note:** Used internally for tracking rule evaluations and missing data warnings.

---

## Functions

### load_policy

```python
load_policy(source, registry=None, *, base_dir=None)
```

Loads and validates a policy from various sources.

**Parameters:**
- `source` (`Any`): Policy source, one of:
  - `dict`: Policy dictionary
  - `str`: Either JSON string (if starts with `"{"`) or file path
  - `Path`: File path to JSON policy file
- `registry` (`RuleRegistry | None`): Registry for validating rules. If `None`, uses default registry.
- `base_dir` (`str | None`): Base directory for resolving relative file paths. If `None`, paths must be absolute.

**Returns:**
- `PolicySpec`: Validated policy specification

**Raises:**
- `PolicyLoadError`: If:
  - Source type is unsupported
  - JSON is invalid
  - File cannot be read
  - Policy is missing required `"name"` field
  - Policy `"name"` is not a non-empty string
  - Policy `"effect"` is not `"allow"` or `"deny"`
  - Policy `"rules"` is not a list
  - Any rule spec is invalid (propagated from `RuleSyntaxError`)

**Validation Behavior:**
- Policy must have non-empty `"name"` (string)
- `"effect"` defaults to `"allow"` if not specified
- `"rules"` defaults to empty list if not specified
- All rule specs are validated by attempting to compile them once
- File paths: If source doesn't start with `{`, treated as file path
  - Relative paths are resolved against `base_dir` if provided
  - Absolute paths are used as-is

**Examples:**
```python
# From dict
policy = load_policy({"name": "test", "effect": "allow", "rules": []})

# From JSON string
policy = load_policy('{"name": "test", "effect": "allow", "rules": []}')

# From file path
policy = load_policy("policy.json")

# From relative file path with base_dir
policy = load_policy("policies/admin.json", base_dir="/etc/app")
```

---

### get_default_registry

```python
get_default_registry()
```

Returns the singleton default rule registry with all built-in rules registered.

**Returns:**
- `RuleRegistry`: The default registry instance

**Note:** The registry is created once and cached. Built-in rules include: `compare`, `all`, `any`, `not`, `truthy`.

---

## Built-in Rules

### compare

Compares a value at a path to an expected value using an operator.

**Specification:**
```json
{
  "type": "compare",
  "path": "user.role",
  "op": "eq",
  "value": "admin"
}
```

**Fields:**
- `path` (required, `string`): Dot-separated path to the value in input data
- `op` (required, `string`): Comparison operator
- `value` (optional, `any`): Expected value (required for most operators)

**Operators:**
- `eq`: Equal to (`==`)
- `ne`: Not equal to (`!=`)
- `gt`: Greater than (`>`)
- `gte`: Greater than or equal (`>=`)
- `lt`: Less than (`<`)
- `lte`: Less than or equal (`<=`)
- `in`: Value is contained in the expected list/collection
- `contains`: Expected value is contained in the actual value
- `exists`: Path exists (value is not `None`)

**Path Resolution:**
- Supports nested dict access via dots: `"user.profile.name"`
- Supports list/tuple indexing: `"items.0.id"`
- Returns `None` if path doesn't exist
- Result is cached per path for performance

**Missing Data Behavior:**
- If path resolves to `None`:
  - `exists` operator returns `False`
  - Other operators:
    - `strict="raise"`: Raises `RuleEvaluationError`
    - `strict="warn"`: Returns `False`, increments `"missing"` metric
    - `strict="off"`: Returns `False` silently

**Examples:**
```python
# Equality
{"type": "compare", "path": "user.id", "op": "eq", "value": 123}

# Greater than
{"type": "compare", "path": "user.age", "op": "gte", "value": 18}

# Membership
{"type": "compare", "path": "user.role", "op": "in", "value": ["admin", "moderator"]}

# Contains
{"type": "compare", "path": "user.permissions", "op": "contains", "value": "write"}

# Existence check
{"type": "compare", "path": "user.email", "op": "exists"}
```

---

### all

Logical AND: All nested rules must evaluate to `True`.

**Specification:**
```json
{
  "type": "all",
  "rules": [
    {"type": "compare", "path": "user.active", "op": "eq", "value": true},
    {"type": "compare", "path": "user.verified", "op": "eq", "value": true}
  ]
}
```

**Fields:**
- `rules` (required, `list`): List of rule specifications

**Behavior:**
- Returns `True` if all rules return `True`
- Returns `False` immediately when first rule returns `False` (short-circuit)
- Returns `True` for empty rules list

---

### any

Logical OR: At least one nested rule must evaluate to `True`.

**Specification:**
```json
{
  "type": "any",
  "rules": [
    {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"},
    {"type": "compare", "path": "user.role", "op": "eq", "value": "owner"}
  ]
}
```

**Fields:**
- `rules` (required, `list`): List of rule specifications

**Behavior:**
- Returns `True` immediately when first rule returns `True` (short-circuit)
- Returns `False` if all rules return `False`
- Returns `False` for empty rules list

---

### not

Logical negation: Inverts the result of a nested rule.

**Specification:**
```json
{
  "type": "not",
  "rule": {
    "type": "compare",
    "path": "user.banned",
    "op": "eq",
    "value": true
  }
}
```

**Fields:**
- `rule` (required, `dict`): Single rule specification to negate

**Behavior:**
- Returns `not rule.evaluate(ctx)`

---

### truthy

Evaluates the truthiness of a value at a path.

**Specification:**
```json
{
  "type": "truthy",
  "path": "user.active"
}
```

**Fields:**
- `path` (required, `string`): Dot-separated path to the value

**Truthiness Rules:**
- `None`: `False`
- `bool`: As-is
- Numbers (`int`, `float`): `False` if `0`, otherwise `True`
- Strings: `False` if empty or one of (case-insensitive): `"0"`, `"false"`, `"no"`, `"off"`, otherwise `True`
- Other types: `True`

**Missing Data Behavior:**
- If path resolves to `None`:
  - `strict="raise"`: Raises `RuleEvaluationError`
  - `strict="warn"`: Returns `False`, increments `"missing"` metric
  - `strict="off"`: Returns `False` silently

---

## Exception Classes

All exceptions inherit from `PolicyEvalError`.

### PolicyEvalError

Base exception class for all policyeval errors.

---

### PolicyLoadError

Raised when a policy cannot be loaded, parsed, or validated.

**Common causes:**
- Invalid JSON syntax
- File not found or not readable
- Missing or invalid `"name"` field
- Invalid `"effect"` value
- `"rules"` is not a list
- Rule spec validation fails during load

---

### UnknownRuleError

Raised when a rule type is not registered in the registry.

**Example:**
```python
# If "custom_rule" is not registered:
load_policy({"name": "test", "effect": "allow", "rules": [
    {"type": "custom_rule"}  # Raises UnknownRuleError
]})
```

---

### RuleSyntaxError

Raised when a rule specification is syntactically invalid.

**Common causes:**
- Rule spec is not a dict
- Missing required `"type"` field
- Missing required fields for specific rule types
- Invalid field types or values

---

### RuleEvaluationError

Raised during rule evaluation when `strict="raise"` and:
- Required data is missing at a path
- Comparison operation fails (e.g., comparing incompatible types)
- Unknown operator in compare rule

---

## Utility Functions

The following utilities are used internally but may be useful for custom rule implementations.

### deep_get

```python
deep_get(obj, path, default=None)
```

Retrieves a value from a nested structure using a dot-separated path.

**Parameters:**
- `obj` (`Any`): Object to traverse (typically dict or list)
- `path` (`str`): Dot-separated path (e.g., `"user.profile.name"`)
- `default` (`Any`): Value to return if path doesn't exist

**Returns:**
- `Any`: Value at path or default

**Behavior:**
- For dicts/mappings: Looks up keys
- For lists/tuples: Converts path segment to integer index
- Supports negative indices for sequences
- Returns default if any segment doesn't exist
- Empty path segments (e.g., `"a..b"`) are ignored

**Example:**
```python
data = {"user": {"name": "Alice", "items": [{"id": 1}, {"id": 2}]}}
deep_get(data, "user.name")           # "Alice"
deep_get(data, "user.items.0.id")     # 1
deep_get(data, "user.age", default=0) # 0 (not found)
```

---

### is_truthy

```python
is_truthy(value)
```

Determines if a value should be considered truthy according to policyeval rules.

**Parameters:**
- `value` (`Any`): Value to check

**Returns:**
- `bool`: Truthiness result

**Rules:** (See `truthy` rule documentation above)

---

### normalize_key

```python
normalize_key(key)
```

Normalizes a string key for case-insensitive lookup.

**Parameters:**
- `key` (`str`): Key to normalize

**Returns:**
- `str`: Normalized key (lowercased, hyphens replaced with underscores, stripped)

**Example:**
```python
normalize_key("User-Role")  # "user_role"
normalize_key("  ADMIN  ")  # "admin"
```

**Note:** Used internally for variable and metric keys in `EvaluationContext`.
