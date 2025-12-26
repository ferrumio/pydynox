"""pydynox - A fast DynamoDB ORM for Python with a Rust core.

This package provides a simple, class-based API to work with DynamoDB.
The Rust core handles serialization, batch processing, and AWS SDK calls.

Example:
    >>> from pydynox import DynamoClient
    >>> client = DynamoClient(region="us-east-1")
    >>> client.ping()
    True
"""

from pydynox._rust import DynamoClient

__version__ = "0.1.0"
__all__ = [
    "DynamoClient",
    "__version__",
]
