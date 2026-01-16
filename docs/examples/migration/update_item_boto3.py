"""boto3: Update item in DynamoDB."""

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

table.update_item(
    Key={"pk": "USER#123", "sk": "PROFILE"},
    UpdateExpression="SET #n = :name, #e = :email",
    ExpressionAttributeNames={"#n": "name", "#e": "email"},
    ExpressionAttributeValues={":name": "Jane Doe", ":email": "jane@example.com"},
)
