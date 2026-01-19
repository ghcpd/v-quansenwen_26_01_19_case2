class PolicyEvalError(Exception):
    """Base exception for all policyeval errors.

    All other exceptions in this package inherit from this class,
    allowing callers to catch all policyeval-related errors with
    a single except clause.
    """


class PolicyLoadError(PolicyEvalError):
    """Raised when a policy cannot be loaded or parsed.

    Common causes:
        - Invalid JSON syntax in policy source
        - File not found or unreadable
        - Missing required fields (e.g., ``name``)
        - Invalid ``effect`` value (must be "allow" or "deny")
        - ``rules`` is not a list
        - Unsupported source type passed to ``load_policy()``
    """


class UnknownRuleError(PolicyEvalError):
    """Raised when a rule type is not found in the registry.

    This occurs when a policy references a rule type (via the ``type``
    field in a rule spec) that has not been registered with the
    ``RuleRegistry``.

    Args:
        The exception message contains the unknown rule type name.
    """


class RuleSyntaxError(PolicyEvalError):
    """Raised when a rule specification is syntactically invalid.

    Common causes:
        - Rule spec is not a dict
        - Missing or empty ``type`` field
        - Missing required fields for specific rule types
          (e.g., ``path`` for compare rules)
        - Invalid field types in rule specification
    """


class RuleEvaluationError(PolicyEvalError):
    """Raised when a rule fails during evaluation.

    Common causes:
        - Missing value at path when ``strict="raise"``
        - Type mismatch during comparison operations
        - Unknown comparison operator
        - Other runtime errors during rule evaluation
    """
