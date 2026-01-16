"""boto3: Get item from DynamoDB."""

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

response = table.get_item(Key={"pk": "USER#123", "sk": "PROFILE"})
user = response.get("Item")

if user:
    print(f"Name: {user.get('name')}")
