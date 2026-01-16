"""boto3: Conditional write to DynamoDB."""

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
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
