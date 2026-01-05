"""DynamoDB client - combines all operations."""

from __future__ import annotations

from pydynox.client._base import BaseClient
from pydynox.client._batch import BatchOperations
from pydynox.client._crud import CrudOperations
from pydynox.client._partiql import PartiqlOperations
from pydynox.client._query import QueryOperations
from pydynox.client._scan import ScanOperations
from pydynox.client._table import TableOperations


class DynamoDBClient(
    BaseClient,
    CrudOperations,
    QueryOperations,
    ScanOperations,
    BatchOperations,
    TableOperations,
    PartiqlOperations,
):
    """DynamoDB client with flexible credential configuration.

    Supports multiple credential sources in order of priority:
    1. Hardcoded credentials (access_key, secret_key, session_token)
    2. AssumeRole (cross-account access)
    3. AWS profile from ~/.aws/credentials (supports SSO)
    4. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    5. Default credential chain (instance profile, container, EKS IRSA, GitHub OIDC)

    Example:
        >>> # Use environment variables or default chain
        >>> client = DynamoDBClient()

        >>> # Use hardcoded credentials
        >>> client = DynamoDBClient(
        ...     access_key="AKIA...",
        ...     secret_key="secret...",
        ...     region="us-east-1"
        ... )

        >>> # Use AWS profile (supports SSO)
        >>> client = DynamoDBClient(profile="my-sso-profile")

        >>> # Use local endpoint (localstack, moto)
        >>> client = DynamoDBClient(endpoint_url="http://localhost:4566")

        >>> # AssumeRole for cross-account access
        >>> client = DynamoDBClient(
        ...     role_arn="arn:aws:iam::123456789012:role/MyRole",
        ...     role_session_name="my-session"
        ... )

        >>> # With rate limiting
        >>> from pydynox import FixedRate, AdaptiveRate
        >>> client = DynamoDBClient(rate_limit=FixedRate(rcu=50))
    """

    pass
