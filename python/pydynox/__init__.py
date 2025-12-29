"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoDBClient
    >>> client = DynamoDBClient(region="us-east-1")
    >>> client.ping()
    True

    >>> from pydynox import Model
    >>> from pydynox.attributes import StringAttribute, NumberAttribute
    >>> class User(Model):
    ...     class Meta:
    ...         table = "users"
    ...     pk = StringAttribute(hash_key=True)
    ...     name = StringAttribute()
    >>> user = User(pk="USER#1", name="John")
    >>> user.save()

    >>> # With Pydantic
    >>> from pydynox.integrations.pydantic import dynamodb_model
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
from pydynox.batch_operations import BatchWriter
from pydynox.client import DynamoDBClient
from pydynox.model import Model
from pydynox.query import QueryResult
from pydynox.transaction import Transaction

__version__ = "0.2.0"

__all__ = [
    # Client
    "BatchWriter",
    "DynamoDBClient",
    "QueryResult",
    "Transaction",
    # Model ORM
    "Model",
    # Version
    "__version__",
]
