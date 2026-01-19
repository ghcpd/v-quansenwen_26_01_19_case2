from __future__ import annotations

import argparse
import json
import sys

from .engine import PolicyEngine
from .loader import load_policy


def _cmd_evaluate(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="policyeval evaluate")
    p.add_argument("--policy", required=True, help="Policy JSON file path or inline JSON")
    p.add_argument("--input", required=True, help="Inline JSON payload")
    p.add_argument("--strict", default=None, help="Strict mode: off|warn|raise")
    p.add_argument("--explain", action="store_true")
    args = p.parse_args(argv)

    policy = load_policy(args.policy)
    payload = json.loads(args.input)

    engine = PolicyEngine()
    decision = engine.evaluate(policy, payload, strict=args.strict, explain=args.explain)
    if args.explain:
        print(json.dumps(decision.explanation, indent=2, sort_keys=True))
    else:
        print("allow" if decision.allowed else "deny")

    return 0 if decision.allowed else 3


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print("Usage: policyeval <command> [args]\n\nCommands:\n  evaluate")
        return 0

    cmd, rest = argv[0], argv[1:]
    if cmd == "evaluate":
        return _cmd_evaluate(rest)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
