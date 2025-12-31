"""Condition classes for building DynamoDB filter expressions.

Most users don't need to import from here. Just use attribute operators:

    User.age > 18
    User.status == "active"
    (User.age > 18) & (User.status == "active")

For dynamic condition building, import And, Or, Not:

    from pydynox.conditions import And
    conditions = [User.status == "active", User.age > 18]
    final = And(*conditions)
"""

from __future__ import annotations

from typing import Union

from pydynox._internal._conditions import (
    ConditionAnd,
    ConditionBeginsWith,
    ConditionBetween,
    ConditionComparison,
    ConditionContains,
    ConditionExists,
    ConditionIn,
    ConditionNot,
    ConditionNotExists,
    ConditionOr,
)

# Type alias for any condition
Condition = Union[
    ConditionComparison,
    ConditionBetween,
    ConditionIn,
    ConditionExists,
    ConditionNotExists,
    ConditionBeginsWith,
    ConditionContains,
    ConditionAnd,
    ConditionOr,
    ConditionNot,
]

__all__ = ["Condition", "And", "Or", "Not"]


def And(*conditions: Condition) -> ConditionAnd:
    """Combine conditions with AND.

    Args:
        *conditions: Two or more conditions to combine.

    Returns:
        Combined condition.

    Example:
        from pydynox.conditions import And
        cond = And(User.age > 18, User.status == "active")
    """
    if len(conditions) < 2:
        raise ValueError("And requires at least 2 conditions")
    result = ConditionAnd(conditions[0], conditions[1])
    for c in conditions[2:]:
        result = ConditionAnd(result, c)
    return result


def Or(*conditions: Condition) -> ConditionOr:
    """Combine conditions with OR.

    Args:
        *conditions: Two or more conditions to combine.

    Returns:
        Combined condition.

    Example:
        from pydynox.conditions import Or
        cond = Or(User.status == "active", User.status == "pending")
    """
    if len(conditions) < 2:
        raise ValueError("Or requires at least 2 conditions")
    result = ConditionOr(conditions[0], conditions[1])
    for c in conditions[2:]:
        result = ConditionOr(result, c)
    return result


def Not(condition: Condition) -> ConditionNot:
    """Negate a condition.

    Args:
        condition: Condition to negate.

    Returns:
        Negated condition.

    Example:
        from pydynox.conditions import Not
        cond = Not(User.deleted.exists())
    """
    return ConditionNot(condition)
