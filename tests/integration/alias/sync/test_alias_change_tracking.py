"""Sync integration tests for change tracking with aliased fields.

Tests that change tracking works correctly when attributes have aliases.
Verifies fix for issue #309: aliased fields were always marked as dirty
because _original stored DynamoDB alias keys but __setattr__ looked up
Python attribute names.
"""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute


class UserAlias(Model):
    model_config = ModelConfig(table="test_table")
    user_id = StringAttribute(partition_key=True, alias="pk")
    sort_key = StringAttribute(sort_key=True, alias="sk")
    first_name = StringAttribute(alias="fn")
    email = StringAttribute(alias="em")
    age = NumberAttribute(alias="a")


@pytest.fixture
def table(dynamo: DynamoDBClient):
    """Set default client for all tests."""
    set_default_client(dynamo)
    yield dynamo


def test_from_dict_not_dirty(table):
    """GIVEN an item loaded via from_dict with alias keys
    WHEN no attributes are changed
    THEN the model should not be dirty.
    """
    data = {"pk": "USER#1", "sk": "PROFILE", "fn": "John", "em": "john@test.com", "a": 30}
    user = UserAlias.from_dict(data)

    assert user.is_dirty is False
    assert user.changed_fields == []


def test_set_same_value_not_dirty(table):
    """GIVEN an item loaded via from_dict with alias keys
    WHEN an attribute is set to the same value it already has
    THEN the model should not be dirty.
    """
    data = {"pk": "USER#1", "sk": "PROFILE", "fn": "John", "em": "john@test.com", "a": 30}
    user = UserAlias.from_dict(data)

    user.first_name = "John"
    user.email = "john@test.com"
    user.age = 30

    assert user.is_dirty is False
    assert user.changed_fields == []


def test_revert_change_clears_dirty(table):
    """GIVEN an item loaded via from_dict with alias keys
    WHEN an attribute is changed and then reverted to original
    THEN the model should not be dirty.
    """
    data = {"pk": "USER#1", "sk": "PROFILE", "fn": "John", "em": "john@test.com", "a": 30}
    user = UserAlias.from_dict(data)

    user.first_name = "Jane"
    assert user.is_dirty is True

    user.first_name = "John"
    assert user.is_dirty is False
    assert user.changed_fields == []


def test_actual_change_is_dirty(table):
    """GIVEN an item loaded via from_dict with alias keys
    WHEN an attribute is changed to a different value
    THEN only that field should be in changed_fields.
    """
    data = {"pk": "USER#1", "sk": "PROFILE", "fn": "John", "em": "john@test.com", "a": 30}
    user = UserAlias.from_dict(data)

    user.first_name = "Jane"

    assert user.is_dirty is True
    assert user.changed_fields == ["first_name"]


def test_save_and_reload_not_dirty(table):
    """GIVEN an item saved to DynamoDB with aliased fields
    WHEN it is loaded back with sync_get
    THEN the model should not be dirty.
    """
    uid = str(uuid.uuid4())[:8]
    user = UserAlias(
        user_id=f"USER#{uid}", sort_key="PROFILE",
        first_name="John", email="john@test.com", age=30,
    )
    user.sync_save()

    loaded = UserAlias.sync_get(user_id=f"USER#{uid}", sort_key="PROFILE")
    assert loaded is not None
    assert loaded.is_dirty is False
    assert loaded.changed_fields == []


def test_save_and_reload_set_same_not_dirty(table):
    """GIVEN an item loaded from DynamoDB with aliased fields
    WHEN attributes are set to the same values
    THEN the model should not be dirty.
    """
    uid = str(uuid.uuid4())[:8]
    user = UserAlias(
        user_id=f"USER#{uid}", sort_key="PROFILE",
        first_name="John", email="john@test.com", age=30,
    )
    user.sync_save()

    loaded = UserAlias.sync_get(user_id=f"USER#{uid}", sort_key="PROFILE")
    assert loaded is not None

    loaded.first_name = "John"
    loaded.email = "john@test.com"
    loaded.age = 30

    assert loaded.is_dirty is False
    assert loaded.changed_fields == []


def test_smart_save_only_sends_changed_fields(table):
    """GIVEN an item loaded from DynamoDB with aliased fields
    WHEN only one field is changed and saved
    THEN the item should reflect the change and other fields stay intact.
    """
    uid = str(uuid.uuid4())[:8]
    user = UserAlias(
        user_id=f"USER#{uid}", sort_key="PROFILE",
        first_name="John", email="john@test.com", age=30,
    )
    user.sync_save()

    loaded = UserAlias.sync_get(user_id=f"USER#{uid}", sort_key="PROFILE")
    assert loaded is not None

    loaded.age = 31
    assert loaded.changed_fields == ["age"]
    loaded.sync_save()

    reloaded = UserAlias.sync_get(user_id=f"USER#{uid}", sort_key="PROFILE")
    assert reloaded is not None
    assert reloaded.first_name == "John"
    assert reloaded.email == "john@test.com"
    assert reloaded.age == 31
    assert reloaded.is_dirty is False


def test_reset_change_tracking_after_save(table):
    """GIVEN an item that was modified and saved
    WHEN checking dirty state after save
    THEN it should be clean.
    """
    uid = str(uuid.uuid4())[:8]
    user = UserAlias(
        user_id=f"USER#{uid}", sort_key="PROFILE",
        first_name="John", email="john@test.com", age=30,
    )
    user.sync_save()

    loaded = UserAlias.sync_get(user_id=f"USER#{uid}", sort_key="PROFILE")
    assert loaded is not None

    loaded.first_name = "Jane"
    loaded.email = "jane@test.com"
    assert loaded.is_dirty is True

    loaded.sync_save()
    assert loaded.is_dirty is False
    assert loaded.changed_fields == []

    # Setting to the new saved values should not be dirty
    loaded.first_name = "Jane"
    assert loaded.is_dirty is False
