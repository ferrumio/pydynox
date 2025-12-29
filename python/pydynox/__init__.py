"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoDBClient
    >>> client = DynamoDBClient(region="us-east-1")
    >>> client.ping()
    True
"""

# Import from Rust core
from pydynox import pydynox_core  # noqa: F401

# Import Python wrappers
from .batch_operations import BatchWriter
from .client import DynamoDBClient
from .exceptions import (
    AccessDeniedError,
    ConditionCheckFailedError,
    CredentialsError,
    PydynoxError,
    SerializationError,
    TableNotFoundError,
    ThrottlingError,
    TransactionCanceledError,
    ValidationError,
)
from .query import QueryResult
from .transaction import Transaction

__version__ = "0.1.1"

__all__ = [
    # Client
    "BatchWriter",
    "DynamoDBClient",
    "QueryResult",
    "Transaction",
    # Exceptions
    "AccessDeniedError",
    "ConditionCheckFailedError",
    "CredentialsError",
    "PydynoxError",
    "SerializationError",
    "TableNotFoundError",
    "ThrottlingError",
    "TransactionCanceledError",
    "ValidationError",
    # Version
    "__version__",
]
