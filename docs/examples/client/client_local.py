"""Client for local development."""

from pydynox import DynamoDBClient

# Connect to DynamoDB Local
client = DynamoDBClient(endpoint_url="http://localhost:8000")

# Connect to LocalStack
client = DynamoDBClient(endpoint_url="http://localhost:4566")
