# PolicyEval API Reference

This is a lightweight reference for the most commonly used APIs.

## Top-level exports

```python
from policyeval import PolicyEngine, load_policy
```

### `load_policy(source, registry=None, base_dir=None)`

Loads a policy definition.

- `source`: JSON string or dict.
- `registry`: optional registry.

Returns a policy object.

### `PolicyEngine`

The main entry point for evaluating policies.

```python
engine = PolicyEngine()
result = engine.evaluate(policy, input_data)
```

`PolicyEngine` uses a registry of rule types.

#### `PolicyEngine.evaluate(policy, input_data, strict=False, now=None, explain=False)`

Evaluates a policy.

- `strict`: if true, missing data causes failure.
- `now`: current time.
- `explain`: include explanation.

Returns `True` if allowed, otherwise `False`.

## Rules

### Compare rule

```json
{"type":"compare","path":"user.role","op":"eq","value":"admin"}
```

Operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`.

## Registry

You can register custom rules:

```python
from policyeval import RuleRegistry

registry = RuleRegistry()
registry.register("my_rule", my_factory)
```
