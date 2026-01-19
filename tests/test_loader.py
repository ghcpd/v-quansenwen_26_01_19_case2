import pytest

from policyeval import PolicyLoadError, load_policy


def test_load_policy_requires_name():
    with pytest.raises(PolicyLoadError):
        load_policy({"effect": "allow", "rules": []})


def test_load_policy_validates_effect():
    with pytest.raises(PolicyLoadError):
        load_policy({"name": "x", "effect": "permit", "rules": []})
