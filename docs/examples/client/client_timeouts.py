from pydynox import DynamoDBClient

# Set connection and read timeouts (in seconds)
client = DynamoDBClient(
    connect_timeout=5.0,  # 5 seconds to establish connection
    read_timeout=30.0,  # 30 seconds to read response
)

# Short timeouts for Lambda (fail fast)
lambda_client = DynamoDBClient(
    connect_timeout=2.0,
    read_timeout=10.0,
)
