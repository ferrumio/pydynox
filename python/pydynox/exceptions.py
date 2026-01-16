"""Custom exceptions for pydynox.

These exceptions mirror the error structure from botocore's ClientError,
making it easy for users familiar with boto3 to handle errors.

Example:
    >>> from pydynox import DynamoDBClient
    >>> from pydynox.exceptions import ResourceNotFoundException, ValidationException
    >>>
    >>> client = DynamoDBClient()
    >>> try:
    ...     client.get_item("nonexistent-table", {"pk": "123"})
    ... except ResourceNotFoundException as e:
    ...     print(f"Table not found: {e}")
"""

from __future__ import annotations

from typing import Any

# Re-export exceptions from Rust core
from pydynox import pydynox_core


class ItemTooLargeException(Exception):
    """Raised when an item exceeds the DynamoDB 400KB size limit.

    This is a Python-only exception raised before calling DynamoDB,
    when max_size is set on the model.

    Attributes:
        size: Actual item size in bytes.
        max_size: Maximum allowed size in bytes.
        item_key: Key of the item (if available).

    Example:
        >>> from pydynox.exceptions import ItemTooLargeException
        >>> try:
        ...     user.save()
        ... except ItemTooLargeException as e:
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
PydynoxException = pydynox_core.PydynoxException
ResourceNotFoundException = pydynox_core.ResourceNotFoundException
ResourceInUseException = pydynox_core.ResourceInUseException
ValidationException = pydynox_core.ValidationException
ConditionalCheckFailedException = pydynox_core.ConditionalCheckFailedException
TransactionCanceledException = pydynox_core.TransactionCanceledException
ProvisionedThroughputExceededException = pydynox_core.ProvisionedThroughputExceededException
AccessDeniedException = pydynox_core.AccessDeniedException
CredentialsException = pydynox_core.CredentialsException
SerializationException = pydynox_core.SerializationException
ConnectionException = pydynox_core.ConnectionException
EncryptionException = pydynox_core.EncryptionException
S3AttributeException = pydynox_core.S3AttributeException

__all__ = [
    "PydynoxException",
    "ResourceNotFoundException",
    "ResourceInUseException",
    "ValidationException",
    "ConditionalCheckFailedException",
    "TransactionCanceledException",
    "ProvisionedThroughputExceededException",
    "AccessDeniedException",
    "CredentialsException",
    "SerializationException",
    "ConnectionException",
    "EncryptionException",
    "S3AttributeException",
    "ItemTooLargeException",
]
