class PolicyEvalError(Exception):
    """Base exception for the policyeval package.

    All exceptions raised by policyeval inherit from this class,
    allowing callers to catch all policyeval-related errors with
    a single except clause.
    """


class PolicyLoadError(PolicyEvalError):
    """Raised when a policy cannot be loaded or parsed.

    Common causes:
        - Invalid JSON syntax in the source
        - Missing required 'name' field
        - Invalid 'effect' value (must be 'allow' or 'deny')
        - 'rules' is not a list
        - File not found or not readable
        - Unsupported source type passed to load_policy()
    """


class UnknownRuleError(PolicyEvalError):
    """Raised when a rule type is not registered in the registry.

    This occurs when a rule specification references a 'type' that
    has not been registered with the RuleRegistry via register().
    """


class RuleSyntaxError(PolicyEvalError):
    """Raised when a rule specification is syntactically invalid.

    Common causes:
        - Rule spec is not a dictionary
        - Missing or empty 'type' field
        - Missing required fields for specific rule types
          (e.g., 'path' for compare rules)
    """


class RuleEvaluationError(PolicyEvalError):
    """Raised when a rule fails during evaluation.

    Common causes:
        - Missing value at path when strict mode is 'raise'
        - Type comparison errors (e.g., comparing incompatible types)
        - Unknown comparison operator
    """
