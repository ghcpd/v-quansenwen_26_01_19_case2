from policyeval import PolicyEngine, load_policy


def test_allow_when_rule_matches():
    policy = load_policy(
        {
            "name": "admin-only",
            "effect": "allow",
            "rules": [
                {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}
            ],
        }
    )
    engine = PolicyEngine()
    decision = engine.evaluate(policy, {"user": {"role": "admin"}})
    assert decision.allowed is True


def test_deny_when_rule_fails_allow_effect():
    policy = load_policy(
        {
            "name": "admin-only",
            "effect": "allow",
            "rules": [
                {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}
            ],
        }
    )
    engine = PolicyEngine()
    decision = engine.evaluate(policy, {"user": {"role": "user"}})
    assert decision.allowed is False


def test_deny_effect_inverts_match():
    policy = load_policy(
        {
            "name": "block-admin",
            "effect": "deny",
            "rules": [
                {"type": "compare", "path": "user.role", "op": "eq", "value": "admin"}
            ],
        }
    )
    engine = PolicyEngine()
    decision = engine.evaluate(policy, {"user": {"role": "admin"}})
    assert decision.allowed is False
