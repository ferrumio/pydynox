"""Unit tests for batch_get retries of unprocessed keys.

DynamoDB can return some keys as UnprocessedKeys. The Rust core sends them
again. These tests use a local HTTP server that acts as DynamoDB, so the real
retry loop runs without Docker or AWS.
"""

import pytest
from pydynox import DynamoDBClient


@pytest.mark.asyncio
@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
async def test_batch_get_retry_keeps_projection(fake_dynamodb, sync):
    """Unprocessed keys are sent again with the same projection."""
    # GIVEN DynamoDB returns key "b" as unprocessed, with only its key and no projection
    fake = fake_dynamodb(
        {
            "BatchGetItem": [
                {
                    "Responses": {"users": [{"pk": {"S": "a"}, "name": {"S": "Ann"}}]},
                    "UnprocessedKeys": {"users": {"Keys": [{"pk": {"S": "b"}}]}},
                },
                {
                    "Responses": {"users": [{"pk": {"S": "b"}, "name": {"S": "Bob"}}]},
                    "UnprocessedKeys": {},
                },
            ]
        }
    )
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=fake.endpoint_url,
        access_key="testing",
        secret_key="testing",
    )
    keys = [{"pk": "a"}, {"pk": "b"}]

    # WHEN batch getting with a projection on a reserved word
    if sync:
        items = client.sync_batch_get("users", keys, projection=["name"])
    else:
        items = await client.batch_get("users", keys, projection=["name"])

    # THEN items from both requests come back
    assert sorted(item["name"] for item in items) == ["Ann", "Bob"]

    # AND the retry asks only for "b", with the same projection and names
    assert len(fake.requests) == 2
    first = fake.requests[0]["RequestItems"]["users"]
    retry = fake.requests[1]["RequestItems"]["users"]
    assert retry["Keys"] == [{"pk": {"S": "b"}}]
    assert retry["ProjectionExpression"] == first["ProjectionExpression"]
    assert retry["ExpressionAttributeNames"] == first["ExpressionAttributeNames"]
    assert retry["ExpressionAttributeNames"] == {"#p0": "name"}
