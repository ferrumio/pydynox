"""boto3: Put item to DynamoDB."""

from typing import Any

import boto3

dynamodb: Any = boto3.resource("dynamodb")  # untyped without boto3-stubs
table = dynamodb.Table("users")

table.put_item(
    Item={
        "pk": "USER#123",
        "sk": "PROFILE",
        "name": "John Doe",
        "email": "john@example.com",
    }
)
