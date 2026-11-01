"""Tests for default_for_new: creation defaults that differ from loading defaults."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import Model, ModelConfig, clear_default_client
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute
from pydynox.generators import AutoGenerate


@pytest.fixture(autouse=True)
def reset_state():
    clear_default_client()
    yield
    clear_default_client()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get_item = AsyncMock(return_value=None)
    client.put_item = AsyncMock(return_value=None)
    client.update_item = AsyncMock(return_value=None)
    client.sync_get_item = MagicMock(return_value=None)
    client.sync_put_item = MagicMock(return_value=None)
    client.sync_update_item = MagicMock(return_value=None)
    return client


@pytest.fixture
def user_model(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        recommendations_enabled = BooleanAttribute(default=False, default_for_new=True)

    User._client_instance = None
    return User


# ========== Direct construction ==========


def test_new_model_uses_default_for_new_when_omitted(user_model):
    # GIVEN a model with default=False and default_for_new=True
    # WHEN a new instance is created without the field
    user = user_model(pk="USER#new")

    # THEN the creation default is used
    assert user.recommendations_enabled is True


def test_new_model_uses_explicit_false_over_default_for_new(user_model):
    user = user_model(pk="USER#new", recommendations_enabled=False)

    assert user.recommendations_enabled is False


def test_new_model_keeps_explicit_none(user_model):
    # GIVEN an optional attribute
    class User(Model):
        model_config = ModelConfig(table="users", client=MagicMock())
        pk = StringAttribute(partition_key=True)
        score = NumberAttribute(default=5, default_for_new=10)

    # WHEN None is passed explicitly
    user = User(pk="USER#1", score=None)

    # THEN None is kept
    assert user.score is None


def test_new_model_explicit_none_default_for_new_means_no_value(mock_client):
    # GIVEN default_for_new=None on an attribute with a non-None default
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        score = NumberAttribute(default=5, default_for_new=None)

    # WHEN a new model is created without the field
    user = User(pk="USER#1")

    # THEN no creation default is applied
    assert user.score is None


def test_new_model_required_default_for_new_none_raises(mock_client):
    # GIVEN a required attribute whose creation default is None
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        score = NumberAttribute(required=True, default=5, default_for_new=None)

    # WHEN a new model is created without the field
    # THEN the required rule applies
    with pytest.raises(ValueError, match="'score' is required"):
        User(pk="USER#1")


def test_new_model_zero_default_for_new_is_used(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        retries = NumberAttribute(default=3, default_for_new=0)

    user = User(pk="USER#1")

    assert user.retries == 0


# ========== Loading stored data ==========


def test_from_dict_missing_field_uses_default_not_default_for_new(user_model):
    # GIVEN a stored record without the field
    # WHEN it is loaded
    user = user_model.from_dict({"pk": "USER#existing"})

    # THEN the read default is used
    assert user.recommendations_enabled is False


def test_from_dict_explicit_value_is_kept(user_model):
    user = user_model.from_dict({"pk": "USER#existing", "recommendations_enabled": True})

    assert user.recommendations_enabled is True


def test_from_dict_stored_none_is_kept(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        score = NumberAttribute(default=5, default_for_new=10)

    user = User.from_dict({"pk": "USER#1", "score": None})

    assert user.score is None


def test_from_dict_uses_alias_missing_field_default(mock_client):
    # GIVEN an aliased attribute with a creation default
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False, default_for_new=True, alias="en")

    # WHEN a stored record lacks the aliased field
    user = User.from_dict({"pk": "USER#1"})

    # THEN the read default is used
    assert user.enabled is False


def test_from_dict_partial_projection_uses_default(user_model):
    # GIVEN a projection that only returns the key
    # WHEN the instance is built
    user = user_model.from_dict({"pk": "USER#1"})

    # THEN no creation default is applied to the projected-out field
    assert user.recommendations_enabled is False


def test_from_dict_missing_required_field_still_raises(mock_client):
    # GIVEN a required attribute with a creation default but no read default
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        flag = BooleanAttribute(required=True, default_for_new=True)

    # WHEN a stored record lacks the field, THEN loading still follows the required rule
    with pytest.raises(ValueError, match="'flag' is required"):
        User.from_dict({"pk": "USER#1"})


def test_from_dict_does_not_leak_loading_flag_after_error(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        flag = BooleanAttribute(required=True, default_for_new=True)

    with pytest.raises(ValueError):
        User.from_dict({"pk": "USER#1"})

    # A later direct construction must use the creation default again
    assert User(pk="USER#2").flag is True


def test_from_dict_custom_constructor_still_receives_fields(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False, default_for_new=True)

        def __init__(self, request_id=None, **kwargs):
            super().__init__(**kwargs)
            self.request_id = request_id

    user = User.from_dict({"pk": "USER#1", "request_id": "abc"})

    assert user.request_id == "abc"
    assert user.enabled is False


# ========== Inheritance ==========


def test_inherited_attribute_keeps_default_for_new(mock_client):
    class Base(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False, default_for_new=True)

    class Child(Base):
        pass

    assert Child(pk="USER#1").enabled is True
    assert Child.from_dict({"pk": "USER#1"}).enabled is False


# ========== Persistence ==========


def test_loaded_fallback_is_not_marked_as_changed(user_model):
    # GIVEN a loaded record that lacks the field
    user = user_model.from_dict({"pk": "USER#existing"})

    # WHEN nothing is changed
    # THEN the read fallback is not tracked as a change
    assert user.is_dirty is False
    assert user.changed_fields == []


def test_explicit_set_on_loaded_record_marks_field_changed(user_model):
    # GIVEN a stored record that lacks the field
    user = user_model.from_dict({"pk": "USER#existing"})

    # WHEN the field is set explicitly, even to the read default
    user.recommendations_enabled = False

    # THEN it is tracked as a change, because the stored item does not have it
    assert user.changed_fields == ["recommendations_enabled"]


def test_new_model_to_dict_includes_default_for_new(user_model):
    user = user_model(pk="USER#new")

    assert user.to_dict() == {"pk": "USER#new", "recommendations_enabled": True}


# ========== Async and sync reads ==========


@pytest.mark.asyncio
async def test_async_get_missing_field_uses_default(user_model, mock_client):
    mock_client.get_item.return_value = {"pk": "USER#1"}

    user = await user_model.get(pk="USER#1")

    assert user is not None
    assert user.recommendations_enabled is False


def test_sync_get_missing_field_uses_default(user_model, mock_client):
    mock_client.sync_get_item.return_value = {"pk": "USER#1"}

    user = user_model.sync_get(pk="USER#1")

    assert user is not None
    assert user.recommendations_enabled is False


# ========== Regression: models that only use default ==========


def test_model_without_default_for_new_uses_default_on_create(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False)

    assert User(pk="USER#1").enabled is False


def test_model_without_default_for_new_uses_default_on_load(mock_client):
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=True)

    assert User.from_dict({"pk": "USER#1"}).enabled is True


# ========== Regressions: save-time auto-generate and object-scoped loading ==========


@pytest.fixture
def item_model(mock_client):
    class Item(Model):
        model_config = ModelConfig(table="items", client=mock_client)
        pk = StringAttribute(partition_key=True)
        token = StringAttribute(default_for_new=AutoGenerate.UUID4)
        name = StringAttribute()

    Item._client_instance = None
    return Item


@pytest.mark.asyncio
async def test_async_save_loaded_item_does_not_generate_default_for_new(item_model, mock_client):
    # GIVEN an old item stored without the auto-generated field
    item = item_model.from_dict({"pk": "ITEM#1", "name": "old"})

    # WHEN only the name changes and the item is saved
    item.name = "new"
    await item.save()

    # THEN no new token is generated and only the changed field is sent
    assert item.token is None
    assert mock_client.update_item.call_args.kwargs["updates"] == {"name": "new"}


def test_sync_save_loaded_item_does_not_generate_default_for_new(item_model, mock_client):
    item = item_model.from_dict({"pk": "ITEM#1", "name": "old"})

    item.name = "new"
    item.sync_save()

    assert item.token is None
    assert mock_client.sync_update_item.call_args.kwargs["updates"] == {"name": "new"}


@pytest.mark.asyncio
async def test_async_save_new_item_generates_default_for_new(item_model):
    item = item_model(pk="ITEM#2", name="new")

    await item.save()

    assert item.token is not None


def test_sync_save_new_item_generates_default_for_new(item_model):
    item = item_model(pk="ITEM#2", name="new")

    item.sync_save()

    assert item.token is not None


def test_nested_model_in_custom_constructor_uses_default_for_new(mock_client):
    class Child(Model):
        model_config = ModelConfig(table="children", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False, default_for_new=True)

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=mock_client)
        pk = StringAttribute(partition_key=True)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.child = Child(pk="CHILD#nested")

    # WHEN a parent is loaded and its constructor creates a new Child
    parent = Parent.from_dict({"pk": "PARENT#1"})

    # THEN the new Child uses the creation default
    assert parent.child.enabled is True


@pytest.mark.asyncio
async def test_task_started_while_loading_does_not_inherit_loading_state(mock_client):
    class Child(Model):
        model_config = ModelConfig(table="children", client=mock_client)
        pk = StringAttribute(partition_key=True)
        enabled = BooleanAttribute(default=False, default_for_new=True)

    async def make_child_later() -> Child:
        await asyncio.sleep(0)
        return Child(pk="CHILD#task")

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=mock_client)
        pk = StringAttribute(partition_key=True)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.later = asyncio.get_running_loop().create_task(make_child_later())

    # WHEN a task created during loading constructs a new Child after from_dict returns
    parent = Parent.from_dict({"pk": "PARENT#1"})
    child = await parent.later

    # THEN the new Child uses the creation default
    assert child.enabled is True
