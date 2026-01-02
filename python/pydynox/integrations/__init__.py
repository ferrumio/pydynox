"""Optional integrations for pydynox.

Supports both Pydantic models and Python dataclasses.

Example:
    >>> from pydynox import DynamoDBClient, dynamodb_model
    >>> from dataclasses import dataclass
    >>>
    >>> client = DynamoDBClient(region="us-east-1")
    >>>
    >>> @dynamodb_model(table="users", hash_key="pk", client=client)
    ... @dataclass
    ... class User:
    ...     pk: str
    ...     name: str
"""

from pydynox.integrations.functions import dynamodb_model

__all__ = ["dynamodb_model"]
