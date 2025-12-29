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

# Re-export exceptions from Rust core
from pydynox import pydynox_core

# These are the actual exception classes from Rust
PydynoxError = pydynox_core.PydynoxError
TableNotFoundError = pydynox_core.TableNotFoundError
ValidationError = pydynox_core.ValidationError
ConditionCheckFailedError = pydynox_core.ConditionCheckFailedError
TransactionCanceledError = pydynox_core.TransactionCanceledError
ThrottlingError = pydynox_core.ThrottlingError
AccessDeniedError = pydynox_core.AccessDeniedError
CredentialsError = pydynox_core.CredentialsError
SerializationError = pydynox_core.SerializationError

__all__ = [
    "PydynoxError",
    "TableNotFoundError",
    "ValidationError",
    "ConditionCheckFailedError",
    "TransactionCanceledError",
    "ThrottlingError",
    "AccessDeniedError",
    "CredentialsError",
    "SerializationError",
]
