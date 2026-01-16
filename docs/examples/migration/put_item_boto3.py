"""boto3: Put item to DynamoDB."""

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

table.put_item(
    Item={
        "pk": "USER#123",
        "sk": "PROFILE",
        "name": "John Doe",
        "email": "john@example.com",
    }
)
