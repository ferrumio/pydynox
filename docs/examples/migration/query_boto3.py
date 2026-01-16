"""boto3: Query items from DynamoDB."""

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("orders")

response = table.query(
    KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
    FilterExpression="amount > :min_amount",
    ExpressionAttributeValues={
        ":pk": "CUSTOMER#123",
        ":prefix": "ORDER#",
        ":min_amount": 100,
    },
)

for order in response["Items"]:
    print(f"Order: {order['sk']}, Amount: {order['amount']}")
