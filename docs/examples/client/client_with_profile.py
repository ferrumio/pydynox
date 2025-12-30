"""Client with AWS profile."""

from pydynox import DynamoDBClient

# Use a named profile from ~/.aws/credentials
client = DynamoDBClient(profile="prod")

# Or specify region with profile
client = DynamoDBClient(
    profile="prod",
    region="eu-west-1",
)
