"""Integration tests for atomic update operations."""

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class User(Model):
    model_config = ModelConfig(table="test_table")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    count = NumberAttribute()
    balance = NumberAttribute()
    tags = ListAttribute()


@pytest.fixture(autouse=True)
def setup_client(dynamo):
    set_default_client(dynamo)


def test_atomic_add_increments_value(dynamo):
    # GIVEN a user with count=0
    user = User(pk="USER#1", sk="PROFILE", name="John", count=0)
    user.save()

    # WHEN we add 1 atomically
    user.update(atomic=[User.count.add(1)])

    # THEN count is incremented
    result = User.get(pk="USER#1", sk="PROFILE")
    assert result.count == 1


def test_atomic_add_decrements_with_negative(dynamo):
    user = User(pk="USER#2", sk="PROFILE", name="John", balance=100)
    user.save()

    user.update(atomic=[User.balance.add(-25)])

    result = User.get(pk="USER#2", sk="PROFILE")
    assert result.balance == 75


def test_atomic_set_updates_value(dynamo):
    user = User(pk="USER#3", sk="PROFILE", name="John", count=0)
    user.save()

    user.update(atomic=[User.name.set("Jane")])

    result = User.get(pk="USER#3", sk="PROFILE")
    assert result.name == "Jane"


def test_atomic_remove_deletes_attribute(dynamo):
    user = User(pk="USER#4", sk="PROFILE", name="John", count=10)
    user.save()

    user.update(atomic=[User.count.remove()])

    result = User.get(pk="USER#4", sk="PROFILE")
    assert result.count is None


def test_atomic_append_adds_to_list(dynamo):
    user = User(pk="USER#5", sk="PROFILE", name="John", tags=["a", "b"])
    user.save()

    user.update(atomic=[User.tags.append(["c", "d"])])

    result = User.get(pk="USER#5", sk="PROFILE")
    assert result.tags == ["a", "b", "c", "d"]


def test_atomic_prepend_adds_to_front(dynamo):
    user = User(pk="USER#6", sk="PROFILE", name="John", tags=["b", "c"])
    user.save()

    user.update(atomic=[User.tags.prepend(["a"])])

    result = User.get(pk="USER#6", sk="PROFILE")
    assert result.tags == ["a", "b", "c"]


def test_atomic_if_not_exists_sets_when_missing(dynamo):
    # GIVEN a user without count attribute
    user = User(pk="USER#7", sk="PROFILE", name="John")
    user.save()

    # WHEN we use if_not_exists
    user.update(atomic=[User.count.if_not_exists(100)])

    # THEN count is set to 100
    result = User.get(pk="USER#7", sk="PROFILE")
    assert result.count == 100


def test_atomic_if_not_exists_keeps_existing(dynamo):
    # GIVEN a user with count=50
    user = User(pk="USER#8", sk="PROFILE", name="John", count=50)
    user.save()

    # WHEN we use if_not_exists
    user.update(atomic=[User.count.if_not_exists(100)])

    # THEN count stays at 50 (existing value kept)
    result = User.get(pk="USER#8", sk="PROFILE")
    assert result.count == 50


def test_multiple_atomic_operations(dynamo):
    # GIVEN a user with count=0 and tags=["a"]
    user = User(pk="USER#9", sk="PROFILE", name="John", count=0, tags=["a"])
    user.save()

    # WHEN we apply multiple atomic operations
    user.update(
        atomic=[
            User.count.add(5),
            User.tags.append(["b"]),
            User.name.set("Jane"),
        ]
    )

    # THEN all operations are applied
    result = User.get(pk="USER#9", sk="PROFILE")
    assert result.count == 5
    assert result.tags == ["a", "b"]
    assert result.name == "Jane"


def test_atomic_with_condition_succeeds(dynamo):
    # GIVEN a user with balance=100
    user = User(pk="USER#COND1", sk="PROFILE", name="John", balance=100)
    user.save()

    # WHEN we subtract 50 with condition balance >= 50
    user.update(
        atomic=[User.balance.add(-50)],
        condition=User.balance >= 50,
    )

    # THEN the update succeeds
    result = User.get(pk="USER#COND1", sk="PROFILE")
    assert result.balance == 50


def test_atomic_with_condition_fails(dynamo):
    # GIVEN a user with balance=30
    user = User(pk="USER#COND2", sk="PROFILE", name="John", balance=30)
    user.save()

    # WHEN we try to subtract 50 with condition balance >= 50
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        user.update(
            atomic=[User.balance.add(-50)],
            condition=User.balance >= 50,
        )

    # AND balance is unchanged
    result = User.get(pk="USER#COND2", sk="PROFILE")
    assert result.balance == 30


def test_atomic_set_and_remove_combined(dynamo):
    user = User(pk="USER#12", sk="PROFILE", name="John", count=10, balance=100)
    user.save()

    user.update(
        atomic=[
            User.name.set("Jane"),
            User.count.remove(),
        ]
    )

    result = User.get(pk="USER#12", sk="PROFILE")
    assert result.name == "Jane"
    assert result.count is None
    assert result.balance == 100


def test_atomic_add_with_string_condition(dynamo):
    user = User(pk="USER#COND3", sk="PROFILE", name="John", balance=200)
    user.save()

    user.update(
        atomic=[User.balance.add(-50)],
        condition=User.name == "John",
    )

    result = User.get(pk="USER#COND3", sk="PROFILE")
    assert result.balance == 150


def test_atomic_add_with_string_condition_fails(dynamo):
    user = User(pk="USER#COND4", sk="PROFILE", name="John", balance=200)
    user.save()

    with pytest.raises(ConditionalCheckFailedException):
        user.update(
            atomic=[User.balance.add(-50)],
            condition=User.name == "Jane",
        )

    result = User.get(pk="USER#COND4", sk="PROFILE")
    assert result.balance == 200


def test_atomic_multiple_ops_with_condition(dynamo):
    user = User(pk="USER#COND5", sk="PROFILE", name="John", count=5, balance=100)
    user.save()

    user.update(
        atomic=[
            User.count.add(1),
            User.balance.add(-10),
        ],
        condition=User.balance >= 10,
    )

    result = User.get(pk="USER#COND5", sk="PROFILE")
    assert result.count == 6
    assert result.balance == 90


def test_atomic_append_with_condition(dynamo):
    user = User(pk="USER#COND6", sk="PROFILE", name="John", tags=["a"], count=10)
    user.save()

    user.update(
        atomic=[User.tags.append(["b"])],
        condition=User.count > 5,
    )

    result = User.get(pk="USER#COND6", sk="PROFILE")
    assert result.tags == ["a", "b"]


def test_atomic_set_with_exists_condition(dynamo):
    user = User(pk="USER#COND7", sk="PROFILE", name="John", count=10)
    user.save()

    user.update(
        atomic=[User.name.set("Jane")],
        condition=User.count.exists(),
    )

    result = User.get(pk="USER#COND7", sk="PROFILE")
    assert result.name == "Jane"


def test_atomic_with_not_exists_condition(dynamo):
    user = User(pk="USER#COND8", sk="PROFILE", name="John")
    user.save()

    user.update(
        atomic=[User.count.if_not_exists(100)],
        condition=User.count.not_exists(),
    )

    result = User.get(pk="USER#COND8", sk="PROFILE")
    assert result.count == 100
