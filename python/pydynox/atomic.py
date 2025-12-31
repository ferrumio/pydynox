"""Atomic update types for DynamoDB operations.

Most users don't need to import from here. Just use attribute methods:

    User.count.add(1)
    User.tags.append(["new"])
    User.temp.remove()

The AtomicOp type is exported for type hints.
"""

from __future__ import annotations

from typing import Union

from pydynox._internal._atomic import (
    AtomicAdd,
    AtomicAppend,
    AtomicIfNotExists,
    AtomicPrepend,
    AtomicRemove,
    AtomicSet,
)

# Type alias for any atomic operation
AtomicOp = Union[
    AtomicSet,
    AtomicAdd,
    AtomicRemove,
    AtomicAppend,
    AtomicPrepend,
    AtomicIfNotExists,
]

__all__ = ["AtomicOp"]
