class PolicyEvalError(Exception):
    """Base error for the policyeval package."""


class PolicyLoadError(PolicyEvalError):
    """Raised when a policy cannot be loaded or parsed."""


class UnknownRuleError(PolicyEvalError):
    """Raised when a rule type is not registered."""


class RuleSyntaxError(PolicyEvalError):
    """Raised when a rule specification is syntactically invalid."""


class RuleEvaluationError(PolicyEvalError):
    """Raised when a rule fails during evaluation."""
