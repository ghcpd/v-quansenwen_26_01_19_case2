# PolicyEval API Reference

This reference documents the public APIs exactly as implemented.

## Top-level exports

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

## Data structures

- ``PolicySpec`` (from ``policyeval.loader``): raw policy specification with fields
	``name`` (non-empty string), ``effect`` (``"allow"`` or ``"deny"``), and
	``rules`` (list of rule spec dicts). Produced by ``load_policy``.
- ``Policy``: compiled policy produced by ``PolicyEngine.compile`` with the same
	``name`` and ``effect`` plus a list of instantiated rule objects.
- ``Decision``: result returned by ``PolicyEngine.evaluate`` with fields
	``allowed``, ``policy``, ``effect``, ``matched``, and optional ``explanation``.
	When ``explain=True``, ``explanation`` contains ``matched``, ``effect``,
	``metrics`` (counters), and ``rules`` (per-rule explanations).

## Loading policies

### load_policy(source, registry=None, base_dir=None) -> PolicySpec

Load a policy from a dict, inline JSON string, or JSON file path.

- ``source``: dict, ``Path``, or string. Strings starting with ``{`` are parsed
	as inline JSON; other strings are treated as file paths. Relative paths use
	``base_dir`` when provided.
- ``registry``: optional ``RuleRegistry`` used to validate rule specs; defaults
	to the process-wide default registry.
- ``base_dir``: base directory for resolving relative paths.

Validation rules:
- ``name`` must be a non-empty string.
- ``effect`` must be ``"allow"`` or ``"deny"`` (defaults to ``"allow"``).
- ``rules`` must be a list. Each rule spec is created once through the registry
	to validate syntax and type names.

Raises ``PolicyLoadError`` on unsupported sources, I/O or JSON parse errors,
invalid fields, or rule validation failures (wrapped ``RuleSyntaxError``).

## PolicyEngine

### PolicyEngine(registry=None, strict="warn")

- ``registry``: optional ``RuleRegistry``; defaults to ``get_default_registry()``.
- ``strict``: default strict mode used during evaluation (``"off"``, ``"warn"``,
	or ``"raise"``).

### compile(spec: PolicySpec) -> Policy

Compiles a ``PolicySpec`` into a ``Policy`` by instantiating each rule via the
registry. Propagates ``RuleSyntaxError`` or ``UnknownRuleError`` from rule
creation.

### evaluate(policy, input_data, strict=None, now=None, explain=False) -> Decision

Evaluates a policy specification or compiled ``Policy`` against ``input_data``.

- ``policy``: ``PolicySpec`` (compiled on the fly) or ``Policy``.
- ``input_data``: arbitrary payload provided to rules.
- ``strict``: overrides engine strict mode (``"off"``, ``"warn"``, ``"raise"``).
- ``now``: optional ``datetime`` injected into the evaluation context; defaults
	to ``datetime.now(timezone.utc)``.
- ``explain``: when True, includes per-rule explanations and counters.

Rules execute in order until one fails; ``matched`` becomes False at the first
failure. ``allowed`` mirrors ``matched`` for ``effect="allow"`` and inverts it
for ``effect="deny"``. Raises ``PolicyLoadError`` for unsupported policy types
and propagates ``RuleEvaluationError`` from rules.

### explain(policy, input_data, strict=None) -> dict

Helper that returns only the explanation produced by ``evaluate(..., explain=True)``.

## Built-in rules

The default registry includes the following rule types:

- **compare**: ``{"type": "compare", "path": <string>, "op": <op>, "value": <value?>}``
	- Operators: ``eq``, ``ne``, ``gt``, ``gte``, ``lt``, ``lte``, ``in``,
		``contains``, ``exists``.
	- Missing path handling: ``exists`` returns False; other operators return
		False and bump the ``missing`` metric in strict ``"warn"`` mode or raise
		``RuleEvaluationError`` in strict ``"raise"`` mode.
- **truthy**: ``{"type": "truthy", "path": <string>}`` treats the value at
	``path`` as boolean using ``is_truthy`` semantics. Missing values behave the
	same as ``compare`` missing handling.
- **all**: ``{"type": "all", "rules": [ ... ]}`` succeeds only when every
	child rule succeeds.
- **any**: ``{"type": "any", "rules": [ ... ]}`` succeeds when any child rule
	succeeds.
- **not**: ``{"type": "not", "rule": { ... }}`` negates the result of the
	inner rule.

## Registry utilities

- ``RuleRegistry.register(type_name, factory)``: register or replace a factory.
- ``RuleRegistry.unregister(type_name)``: remove a factory if present.
- ``RuleRegistry.create(spec)``: instantiate a rule from a spec; raises
	``RuleSyntaxError`` for invalid specs and ``UnknownRuleError`` for unknown
	types.
- ``get_default_registry()``: returns the shared registry populated with the
	built-in rule factories.

## CLI

``policyeval.cli`` provides ``policyeval evaluate``.

- ``--policy``: required inline JSON or path to a policy JSON file.
- ``--input``: required inline JSON payload.
- ``--strict``: strict mode string (``off`` | ``warn`` | ``raise``); defaults to
	the engine default (``warn``).
- ``--explain``: when set, prints JSON explanation; otherwise prints ``allow`` or
	``deny``.

Exit codes: ``0`` when the decision is allowed, ``3`` when denied, ``2`` for
unknown commands. Invoking with ``-h`` or ``--help`` prints usage and exits 0.
