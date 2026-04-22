"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from typing import ClassVar
    >>> from pydynox import DynamoDBClient, Model, DynamoConfig
    >>> from pydynox.attributes import StringAttribute
    >>>
    >>> client = DynamoDBClient(region="us-east-1")
    >>>
    >>> class User(Model):
    ...     dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(
    ...         table="users", client=client
    ...     )
    ...     pk = StringAttribute(partition_key=True)
    ...     name = StringAttribute()
    >>>
    >>> user = User(pk="USER#1", name="John")
    >>> user.save()
"""

from __future__ import annotations

from pydynox import pydynox_core  # noqa: F401
from pydynox._internal._logging import set_correlation_id, set_logger
from pydynox._internal._tracing import disable_tracing, enable_tracing
from pydynox.batch_operations import BatchWriter, SyncBatchWriter
from pydynox.client import DynamoDBClient
from pydynox.collection import Collection, CollectionResult
from pydynox.conditions import Condition
from pydynox.config import (
    DynamoConfig,
    ModelConfig,
    clear_default_client,
    get_default_client,
    set_default_client,
)
from pydynox.dynamo import (
    Dynamo,
    DynamoBinary,
    DynamoBoolean,
    DynamoFieldMarker,
    DynamoNumber,
    DynamoString,
)
from pydynox.generators import AutoGenerate
from pydynox.integrations.functions import dynamodb_model
from pydynox.model import Model
from pydynox.transaction import SyncTransaction, Transaction
from pydynox.version import VERSION, version_info

__version__ = VERSION


__all__ = [
    # Core
    "DynamoDBClient",
    "Model",
    "DynamoConfig",
    # Back-compat alias for DynamoConfig
    "ModelConfig",
    # Annotated field markers
    "Dynamo",
    "DynamoString",
    "DynamoNumber",
    "DynamoBoolean",
    "DynamoBinary",
    "DynamoFieldMarker",
    # Operations
    "BatchWriter",
    "SyncBatchWriter",
    "Collection",
    "CollectionResult",
    "Condition",
    "SyncTransaction",
    "Transaction",
    # Generators
    "AutoGenerate",
    # Integrations
    "dynamodb_model",
    # Client config
    "set_default_client",
    "get_default_client",
    "clear_default_client",
    # Logging
    "set_logger",
    "set_correlation_id",
    # Tracing
    "enable_tracing",
    "disable_tracing",
    # Version
    "__version__",
    "version_info",
]
