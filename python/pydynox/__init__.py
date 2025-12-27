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
from .query import QueryResult

__version__ = "0.1.0"

__all__ = [
    "BatchWriter",
    "DynamoClient",
    "QueryResult",
    "__version__",
]
