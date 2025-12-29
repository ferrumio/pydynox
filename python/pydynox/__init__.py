"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoClient
    >>> client = DynamoClient(region="us-east-1")
    >>> client.ping()
    True
"""

# Import from Rust core
from pydynox import pydynox_core  # noqa: F401

# Import Python wrappers
from .batch_operations import BatchWriter
from .client import DynamoClient
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

__version__ = "0.1.0"

__all__ = [
    # Client
    "BatchWriter",
    "DynamoClient",
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
