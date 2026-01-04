from pydynox import DynamoDBClient

# Configure max retry attempts
client = DynamoDBClient(
    max_retries=5,  # Retry up to 5 times on transient errors
)

# Combined with timeouts
client = DynamoDBClient(
    connect_timeout=5.0,
    read_timeout=30.0,
    max_retries=3,
)
