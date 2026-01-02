"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoDBClient, set_default_client
    >>> client = DynamoDBClient(region="us-east-1")
    >>> set_default_client(client)
    >>> client.ping()
    True

    >>> from pydynox import Model, ModelConfig
    >>> from pydynox.attributes import StringAttribute, NumberAttribute
    >>> class User(Model):
    ...     model_config = ModelConfig(table="users")
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

    >>> # With rate limiting
    >>> from pydynox import DynamoDBClient, FixedRate
    >>> client = DynamoDBClient(rate_limit=FixedRate(rcu=50))

    >>> # Access metrics from operations
    >>> item = client.get_item("users", {"pk": "USER#1"})
    >>> print(item["name"])              # Works like a normal dict
    >>> print(item.metrics.duration_ms)  # Access metrics

    >>> # Custom logger with SDK debug
    >>> from pydynox import set_logger
    >>> from aws_lambda_powertools import Logger
    >>> set_logger(Logger(), sdk_debug=True)
"""

from __future__ import annotations

# Import from Rust core
from pydynox import pydynox_core  # noqa: F401

# Import Python wrappers
from pydynox._internal._logging import (
    set_correlation_id,
    set_logger,
)
from pydynox._internal._metrics import OperationMetrics
from pydynox.batch_operations import BatchWriter
from pydynox.client import DynamoDBClient
from pydynox.conditions import Condition
from pydynox.config import (
    ModelConfig,
    clear_default_client,
    get_default_client,
    set_default_client,
)
from pydynox.generators import AutoGenerate
from pydynox.indexes import GlobalSecondaryIndex
from pydynox.model import Model
from pydynox.query import QueryResult
from pydynox.transaction import Transaction

__version__ = "0.9.0"

__all__ = [
    # Client
    "BatchWriter",
    "DynamoDBClient",
    "QueryResult",
    "Transaction",
    # Model ORM
    "AutoGenerate",
    "Condition",
    "GlobalSecondaryIndex",
    "Model",
    "ModelConfig",
    # Metrics (public class for type hints)
    "OperationMetrics",
    # Logging
    "set_logger",
    "set_correlation_id",
    # Client config
    "set_default_client",
    "get_default_client",
    "clear_default_client",
    # Version
    "__version__",
]
