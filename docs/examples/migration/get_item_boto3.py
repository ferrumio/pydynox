"""boto3: Get item from DynamoDB."""

from typing import Any

import boto3

dynamodb: Any = boto3.resource("dynamodb")  # untyped without boto3-stubs
table = dynamodb.Table("users")

response = table.get_item(Key={"pk": "USER#123", "sk": "PROFILE"})
user = response.get("Item")

if user:
    print(f"Name: {user.get('name')}")
