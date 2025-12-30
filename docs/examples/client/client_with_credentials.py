"""Client with explicit credentials."""

from pydynox import DynamoDBClient

# Hardcoded credentials (not recommended for production)
client = DynamoDBClient(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region="us-east-1",
)

# With session token (for temporary credentials)
client = DynamoDBClient(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    session_token="FwoGZXIvYXdzEBY...",
    region="us-east-1",
)
