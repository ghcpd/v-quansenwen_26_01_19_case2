"""Command-line interface for PolicyEval.

This module provides the CLI for evaluating policies from the command line.

Usage:
    python -m policyeval evaluate --policy <path-or-json> --input <json> [options]

Commands:
    evaluate    Evaluate a policy against a JSON input payload.

Exit codes:
    0: Policy allowed the action
    2: Unknown command
    3: Policy denied the action
"""

from __future__ import annotations

import argparse
import json
import sys

from .engine import PolicyEngine
from .loader import load_policy


def _cmd_evaluate(argv: list[str]) -> int:
    """Execute the 'evaluate' command.

    Args:
        argv: Command-line arguments after 'evaluate'.

    Returns:
        int: Exit code (0 if allowed, 3 if denied).
    """
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
    """Main entry point for the policyeval CLI.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        int: Exit code.
            - 0: Success (policy allowed or help shown)
            - 2: Unknown command
            - 3: Policy denied the action
    """
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
