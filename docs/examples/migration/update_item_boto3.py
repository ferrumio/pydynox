"""boto3: Update item in DynamoDB."""

from typing import Any

import boto3

dynamodb: Any = boto3.resource("dynamodb")  # untyped without boto3-stubs
table = dynamodb.Table("users")

table.update_item(
    Key={"pk": "USER#123", "sk": "PROFILE"},
    UpdateExpression="SET #n = :name, #e = :email",
    ExpressionAttributeNames={"#n": "name", "#e": "email"},
    ExpressionAttributeValues={":name": "Jane Doe", ":email": "jane@example.com"},
)
