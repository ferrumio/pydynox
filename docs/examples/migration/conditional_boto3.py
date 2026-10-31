"""boto3: Conditional write to DynamoDB."""

from typing import Any

import boto3
from botocore.exceptions import ClientError

dynamodb: Any = boto3.resource("dynamodb")  # untyped without boto3-stubs
table = dynamodb.Table("users")

try:
    table.put_item(
        Item={"pk": "USER#123", "sk": "PROFILE", "name": "John"},
        ConditionExpression="attribute_not_exists(pk)",
    )
    print("User created")
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        print("User already exists")
