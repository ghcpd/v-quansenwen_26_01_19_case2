class PolicyEvalError(Exception):
    """Base error for the policyeval package."""


class PolicyLoadError(PolicyEvalError):
    """Raised when a policy cannot be loaded, parsed, or validated.

    Common causes:
        - Invalid JSON syntax
        - File not found or not readable
        - Missing or invalid 'name' field
        - Invalid 'effect' value (must be 'allow' or 'deny')
        - 'rules' is not a list
        - Rule spec validation fails during load
    """


class UnknownRuleError(PolicyEvalError):
    """Raised when a rule type is not registered in the registry.

    This occurs when a policy references a rule type that hasn't been
    registered via RuleRegistry.register().
    """


class RuleSyntaxError(PolicyEvalError):
    """Raised when a rule specification is syntactically invalid.

    Common causes:
        - Rule spec is not a dict
        - Missing required 'type' field
        - Missing required fields for specific rule types
        - Invalid field types or values
    """


class RuleEvaluationError(PolicyEvalError):
    """Raised when a rule fails during evaluation.

    Common causes (when strict="raise"):
        - Required data is missing at a path
        - Comparison operation fails (e.g., comparing incompatible types)
        - Unknown operator in compare rule
    """
