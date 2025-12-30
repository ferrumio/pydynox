"""Basic client setup."""

from pydynox import DynamoDBClient

# Use default credentials (env vars, instance profile, etc.)
client = DynamoDBClient()

# Check connection
if client.ping():
    print("Connected!")
