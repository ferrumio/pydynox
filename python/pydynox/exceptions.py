"""Custom exceptions for pydynox.

These exceptions mirror the error structure from botocore's ClientError,
making it easy for users familiar with boto3 to handle errors.

Example:
    >>> from pydynox import DynamoDBClient
    >>> from pydynox.exceptions import TableNotFoundError, ValidationError
    >>>
    >>> client = DynamoDBClient()
    >>> try:
    ...     client.get_item("nonexistent-table", {"pk": "123"})
    ... except TableNotFoundError as e:
    ...     print(f"Table not found: {e}")
"""

from __future__ import annotations

from typing import Any

# Re-export exceptions from Rust core
from pydynox import pydynox_core


class ItemTooLargeError(Exception):
    """Raised when an item exceeds the DynamoDB 400KB size limit.

    This is a Python-only exception raised before calling DynamoDB,
    when max_size is set on the model.

    Attributes:
        size: Actual item size in bytes.
        max_size: Maximum allowed size in bytes.
        item_key: Key of the item (if available).

    Example:
        >>> from pydynox.exceptions import ItemTooLargeError
        >>> try:
        ...     user.save()
        ... except ItemTooLargeError as e:
        ...     print(f"Item too large: {e.size} bytes (max: {e.max_size})")
    """

    def __init__(
        self,
        size: int,
        max_size: int,
        item_key: dict[str, Any] | None = None,
    ):
        self.size = size
        self.max_size = max_size
        self.item_key = item_key
        super().__init__(f"Item size {size} bytes exceeds max_size {max_size} bytes")


# These are the actual exception classes from Rust
PydynoxError = pydynox_core.PydynoxError
TableNotFoundError = pydynox_core.TableNotFoundError
TableAlreadyExistsError = pydynox_core.TableAlreadyExistsError
ValidationError = pydynox_core.ValidationError
ConditionCheckFailedError = pydynox_core.ConditionCheckFailedError
TransactionCanceledError = pydynox_core.TransactionCanceledError
ThrottlingError = pydynox_core.ThrottlingError
AccessDeniedError = pydynox_core.AccessDeniedError
CredentialsError = pydynox_core.CredentialsError
SerializationError = pydynox_core.SerializationError
ConnectionError = pydynox_core.ConnectionError
EncryptionError = pydynox_core.EncryptionError
S3AttributeError = pydynox_core.S3AttributeError

__all__ = [
    "PydynoxError",
    "TableNotFoundError",
    "TableAlreadyExistsError",
    "ValidationError",
    "ConditionCheckFailedError",
    "TransactionCanceledError",
    "ThrottlingError",
    "AccessDeniedError",
    "CredentialsError",
    "SerializationError",
    "ConnectionError",
    "EncryptionError",
    "S3AttributeError",
    "ItemTooLargeError",
]
