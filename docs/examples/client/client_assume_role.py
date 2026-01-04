from pydynox import DynamoDBClient

# AssumeRole for cross-account access
client = DynamoDBClient(
    role_arn="arn:aws:iam::123456789012:role/MyRole",
    role_session_name="my-session",  # optional, defaults to "pydynox-session"
)

# With external ID (for third-party access)
client = DynamoDBClient(
    role_arn="arn:aws:iam::123456789012:role/MyRole",
    external_id="my-external-id",
)
