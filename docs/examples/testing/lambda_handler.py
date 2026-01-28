"""Testing AWS Lambda handlers with pydynox."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


# Lambda handlers are sync, but can run async code inside
def create_user_handler(event, context):
    """Lambda handler that creates a user."""

    async def _create():
        user_id = event["user_id"]
        name = event["name"]

        user = User(pk=f"USER#{user_id}", name=name)
        await user.save()

        return {"statusCode": 201, "body": f"Created user {user_id}"}

    return asyncio.run(_create())


def get_user_handler(event, context):
    """Lambda handler that gets a user."""

    async def _get():
        user_id = event["user_id"]

        user = await User.get(pk=f"USER#{user_id}")
        if not user:
            return {"statusCode": 404, "body": "User not found"}

        return {"statusCode": 200, "body": {"name": user.name}}

    return asyncio.run(_get())


# Tests - no moto, no localstack, no DynamoDB Local!
def test_create_user_handler(pydynox_memory_backend):
    """Test the create user Lambda handler."""
    event = {"user_id": "123", "name": "John"}

    response = create_user_handler(event, None)

    assert response["statusCode"] == 201

    # Verify user was created (sync in test)
    user = User.sync_get(pk="USER#123")
    assert user is not None
    assert user.name == "John"


def test_get_user_handler(pydynox_memory_backend):
    """Test the get user Lambda handler."""
    # Setup: create a user first
    User(pk="USER#123", name="Jane").sync_save()

    event = {"user_id": "123"}
    response = get_user_handler(event, None)

    assert response["statusCode"] == 200
    assert response["body"]["name"] == "Jane"


def test_get_user_not_found(pydynox_memory_backend):
    """Test getting a non-existent user."""
    event = {"user_id": "999"}

    response = get_user_handler(event, None)

    assert response["statusCode"] == 404
