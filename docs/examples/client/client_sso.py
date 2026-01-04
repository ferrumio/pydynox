from pydynox import DynamoDBClient

# Use an SSO profile configured with `aws configure sso`
# Run `aws sso login --profile my-sso-profile` first
client = DynamoDBClient(profile="my-sso-profile")
