# PolicyEval

PolicyEval is a small configuration-driven policy evaluation engine.
It loads policies from JSON and evaluates them against an input payload.

This repository intentionally simulates a real project where implementation evolved faster than documentation.

## Quick start

### Install (editable)

```bash
python -m pip install -e .
```

### Evaluate a policy from a file

```bash
python -m policyeval.cli evaluate --policy examples/policy.json --input '{"user":{"role":"admin"}}'
```

### Evaluate programmatically

```python
from policyeval import PolicyEngine, load_policy

policy = load_policy({
    "name": "admin-only",
    "effect": "allow",
    "rules": [
        {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}
    ],
})

engine = PolicyEngine()
result = engine.evaluate(policy, {"user": {"role": "admin"}})
print(result.allowed)
```

## Concepts

- **Policy**: A JSON document with a name, an effect, and a list of rules.
- **Rule**: A small predicate that evaluates to true/false for a given input.
- **Registry**: A mapping from rule type names (e.g. `compare`) to rule factories.

## CLI

- `policyeval.cli evaluate` evaluates a policy with a JSON input payload.

## Documentation

- API reference: see API.md

## License

MIT
