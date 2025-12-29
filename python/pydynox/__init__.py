"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoDBClient
    >>> client = DynamoDBClient(region="us-east-1")
    >>> client.ping()
    True

    >>> from pydynox import Model, StringAttribute, NumberAttribute
    >>> class User(Model):
    ...     class Meta:
    ...         table = "users"
    ...     pk = StringAttribute(hash_key=True)
    ...     name = StringAttribute()
    >>> user = User(pk="USER#1", name="John")
    >>> user.save()

    >>> # With Pydantic
    >>> from pydynox import dynamodb_model
    >>> from pydantic import BaseModel
    >>> @dynamodb_model(table="users", hash_key="pk")
    ... class User(BaseModel):
    ...     pk: str
    ...     name: str
    >>> user = User(pk="USER#1", name="John")
    >>> user.save()
"""

# Import from Rust core
from pydynox import pydynox_core  # noqa: F401

# Import Python wrappers
from .attributes import (
    Attribute,
    BinaryAttribute,
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
)
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
from .model import Model
from .pydantic_integration import dynamodb_model, from_pydantic
from .query import QueryResult
from .transaction import Transaction

__version__ = "0.2.0"

__all__ = [
    # Client
    "BatchWriter",
    "DynamoDBClient",
    "QueryResult",
    "Transaction",
    # Model ORM
    "Model",
    "Attribute",
    "StringAttribute",
    "NumberAttribute",
    "BooleanAttribute",
    "BinaryAttribute",
    "ListAttribute",
    "MapAttribute",
    # Pydantic integration
    "dynamodb_model",
    "from_pydantic",
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
