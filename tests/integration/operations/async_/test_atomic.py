"""Integration tests for atomic update operations."""

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class User(Model):
    model_config = ModelConfig(table="test_table")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    count = NumberAttribute()
    balance = NumberAttribute()
    tags = ListAttribute()


@pytest.fixture(autouse=True)
def setup_client(dynamo):
    set_default_client(dynamo)


@pytest.mark.asyncio
async def test_atomic_add_increments_value(dynamo):
    # GIVEN a user with count=0
    user = User(pk="USER#1", sk="PROFILE", name="John", count=0)
    await user.save()

    # WHEN we add 1 atomically
    await user.update(atomic=[User.count.add(1)])

    # THEN count is incremented
    result = await User.get(pk="USER#1", sk="PROFILE")
    assert result.count == 1


@pytest.mark.asyncio
async def test_atomic_add_decrements_with_negative(dynamo):
    user = User(pk="USER#2", sk="PROFILE", name="John", balance=100)
    await user.save()

    await user.update(atomic=[User.balance.add(-25)])

    result = await User.get(pk="USER#2", sk="PROFILE")
    assert result.balance == 75


@pytest.mark.asyncio
async def test_atomic_set_updates_value(dynamo):
    user = User(pk="USER#3", sk="PROFILE", name="John", count=0)
    await user.save()

    await user.update(atomic=[User.name.set("Jane")])

    result = await User.get(pk="USER#3", sk="PROFILE")
    assert result.name == "Jane"


@pytest.mark.asyncio
async def test_atomic_remove_deletes_attribute(dynamo):
    user = User(pk="USER#4", sk="PROFILE", name="John", count=10)
    await user.save()

    await user.update(atomic=[User.count.remove()])

    result = await User.get(pk="USER#4", sk="PROFILE")
    assert result.count is None


@pytest.mark.asyncio
async def test_atomic_append_adds_to_list(dynamo):
    user = User(pk="USER#5", sk="PROFILE", name="John", tags=["a", "b"])
    await user.save()

    await user.update(atomic=[User.tags.append(["c", "d"])])

    result = await User.get(pk="USER#5", sk="PROFILE")
    assert result.tags == ["a", "b", "c", "d"]


@pytest.mark.asyncio
async def test_atomic_prepend_adds_to_front(dynamo):
    user = User(pk="USER#6", sk="PROFILE", name="John", tags=["b", "c"])
    await user.save()

    await user.update(atomic=[User.tags.prepend(["a"])])

    result = await User.get(pk="USER#6", sk="PROFILE")
    assert result.tags == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_atomic_if_not_exists_sets_when_missing(dynamo):
    # GIVEN a user without count attribute
    user = User(pk="USER#7", sk="PROFILE", name="John")
    await user.save()

    # WHEN we use if_not_exists
    await user.update(atomic=[User.count.if_not_exists(100)])

    # THEN count is set to 100
    result = await User.get(pk="USER#7", sk="PROFILE")
    assert result.count == 100


@pytest.mark.asyncio
async def test_atomic_if_not_exists_keeps_existing(dynamo):
    # GIVEN a user with count=50
    user = User(pk="USER#8", sk="PROFILE", name="John", count=50)
    await user.save()

    # WHEN we use if_not_exists
    await user.update(atomic=[User.count.if_not_exists(100)])

    # THEN count stays at 50 (existing value kept)
    result = await User.get(pk="USER#8", sk="PROFILE")
    assert result.count == 50


@pytest.mark.asyncio
async def test_multiple_atomic_operations(dynamo):
    # GIVEN a user with count=0 and tags=["a"]
    user = User(pk="USER#9", sk="PROFILE", name="John", count=0, tags=["a"])
    await user.save()

    # WHEN we apply multiple atomic operations
    await user.update(
        atomic=[
            User.count.add(5),
            User.tags.append(["b"]),
            User.name.set("Jane"),
        ]
    )

    # THEN all operations are applied
    result = await User.get(pk="USER#9", sk="PROFILE")
    assert result.count == 5
    assert result.tags == ["a", "b"]
    assert result.name == "Jane"


@pytest.mark.asyncio
async def test_atomic_with_condition_succeeds(dynamo):
    # GIVEN a user with balance=100
    user = User(pk="USER#COND1", sk="PROFILE", name="John", balance=100)
    await user.save()

    # WHEN we subtract 50 with condition balance >= 50
    await user.update(
        atomic=[User.balance.add(-50)],
        condition=User.balance >= 50,
    )

    # THEN the update succeeds
    result = await User.get(pk="USER#COND1", sk="PROFILE")
    assert result.balance == 50


@pytest.mark.asyncio
async def test_atomic_with_condition_fails(dynamo):
    # GIVEN a user with balance=30
    user = User(pk="USER#COND2", sk="PROFILE", name="John", balance=30)
    await user.save()

    # WHEN we try to subtract 50 with condition balance >= 50
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        await user.update(
            atomic=[User.balance.add(-50)],
            condition=User.balance >= 50,
        )

    # AND balance is unchanged
    result = await User.get(pk="USER#COND2", sk="PROFILE")
    assert result.balance == 30


@pytest.mark.asyncio
async def test_atomic_set_and_remove_combined(dynamo):
    user = User(pk="USER#12", sk="PROFILE", name="John", count=10, balance=100)
    await user.save()

    await user.update(
        atomic=[
            User.name.set("Jane"),
            User.count.remove(),
        ]
    )

    result = await User.get(pk="USER#12", sk="PROFILE")
    assert result.name == "Jane"
    assert result.count is None
    assert result.balance == 100


@pytest.mark.asyncio
async def test_atomic_add_with_string_condition(dynamo):
    user = User(pk="USER#COND3", sk="PROFILE", name="John", balance=200)
    await user.save()

    await user.update(
        atomic=[User.balance.add(-50)],
        condition=User.name == "John",
    )

    result = await User.get(pk="USER#COND3", sk="PROFILE")
    assert result.balance == 150


@pytest.mark.asyncio
async def test_atomic_add_with_string_condition_fails(dynamo):
    user = User(pk="USER#COND4", sk="PROFILE", name="John", balance=200)
    await user.save()

    with pytest.raises(ConditionalCheckFailedException):
        await user.update(
            atomic=[User.balance.add(-50)],
            condition=User.name == "Jane",
        )

    result = await User.get(pk="USER#COND4", sk="PROFILE")
    assert result.balance == 200


@pytest.mark.asyncio
async def test_atomic_multiple_ops_with_condition(dynamo):
    user = User(pk="USER#COND5", sk="PROFILE", name="John", count=5, balance=100)
    await user.save()

    await user.update(
        atomic=[
            User.count.add(1),
            User.balance.add(-10),
        ],
        condition=User.balance >= 10,
    )

    result = await User.get(pk="USER#COND5", sk="PROFILE")
    assert result.count == 6
    assert result.balance == 90


@pytest.mark.asyncio
async def test_atomic_append_with_condition(dynamo):
    user = User(pk="USER#COND6", sk="PROFILE", name="John", tags=["a"], count=10)
    await user.save()

    await user.update(
        atomic=[User.tags.append(["b"])],
        condition=User.count > 5,
    )

    result = await User.get(pk="USER#COND6", sk="PROFILE")
    assert result.tags == ["a", "b"]


@pytest.mark.asyncio
async def test_atomic_set_with_exists_condition(dynamo):
    user = User(pk="USER#COND7", sk="PROFILE", name="John", count=10)
    await user.save()

    await user.update(
        atomic=[User.name.set("Jane")],
        condition=User.count.exists(),
    )

    result = await User.get(pk="USER#COND7", sk="PROFILE")
    assert result.name == "Jane"


@pytest.mark.asyncio
async def test_atomic_with_not_exists_condition(dynamo):
    user = User(pk="USER#COND8", sk="PROFILE", name="John")
    await user.save()

    await user.update(
        atomic=[User.count.if_not_exists(100)],
        condition=User.count.not_exists(),
    )

    result = await User.get(pk="USER#COND8", sk="PROFILE")
    assert result.count == 100
