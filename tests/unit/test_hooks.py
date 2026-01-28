"""Tests for lifecycle hooks."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import Model, ModelConfig, clear_default_client
from pydynox.attributes import StringAttribute
from pydynox.hooks import (
    HookType,
    after_delete,
    after_load,
    after_save,
    after_update,
    before_delete,
    before_save,
    before_update,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


@pytest.fixture
def mock_client():
    """Create a mock DynamoDB client with async methods."""
    client = MagicMock()
    client._client = MagicMock()
    # Async methods
    client.put_item = AsyncMock()
    client.delete_item = AsyncMock()
    client.update_item = AsyncMock(return_value={})
    return client


def test_hook_decorator_sets_hook_type():
    """Test that decorators set _hook_type attribute."""

    # GIVEN a function decorated with before_save
    @before_save
    def my_hook(self):
        pass

    # THEN _hook_type should be set
    assert my_hook._hook_type == HookType.BEFORE_SAVE


@pytest.mark.parametrize(
    "decorator,expected_type",
    [
        pytest.param(before_save, HookType.BEFORE_SAVE, id="before_save"),
        pytest.param(after_save, HookType.AFTER_SAVE, id="after_save"),
        pytest.param(before_delete, HookType.BEFORE_DELETE, id="before_delete"),
        pytest.param(after_delete, HookType.AFTER_DELETE, id="after_delete"),
        pytest.param(before_update, HookType.BEFORE_UPDATE, id="before_update"),
        pytest.param(after_update, HookType.AFTER_UPDATE, id="after_update"),
        pytest.param(after_load, HookType.AFTER_LOAD, id="after_load"),
    ],
)
def test_all_hook_decorators(decorator, expected_type):
    """Test all hook decorators set correct type."""

    # GIVEN a function decorated with the hook decorator
    @decorator
    def hook(self):
        pass

    # THEN _hook_type should match expected type
    assert hook._hook_type == expected_type


def test_model_collects_hooks(mock_client):
    """Test that Model metaclass collects hooks."""

    # GIVEN a model with before_save and after_save hooks
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            pass

        @after_save
        def notify(self):
            pass

    # THEN hooks should be collected
    assert len(User._hooks[HookType.BEFORE_SAVE]) == 1
    assert len(User._hooks[HookType.AFTER_SAVE]) == 1


def test_model_inherits_hooks(mock_client):
    """Test that hooks are inherited from parent class."""

    # GIVEN a base model with a hook
    class BaseModel(Model):
        model_config = ModelConfig(table="base", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_save
        def base_validate(self):
            pass

    # AND a child model with its own hook
    class User(BaseModel):
        model_config = ModelConfig(table="users", client=mock_client)

        @before_save
        def user_validate(self):
            pass

    # THEN child should have both hooks
    assert len(User._hooks[HookType.BEFORE_SAVE]) == 2


@pytest.mark.asyncio
async def test_before_save_hook_runs(mock_client):
    """Test that before_save hook runs before save."""
    # GIVEN a model with a before_save hook that logs calls
    call_order = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            call_order.append("before_save")

    User._client_instance = None

    user = User(pk="USER#1")

    # WHEN we save
    await user.save()

    # THEN before_save should have been called
    assert "before_save" in call_order
    mock_client.put_item.assert_called_once()


@pytest.mark.asyncio
async def test_after_save_hook_runs(mock_client):
    """Test that after_save hook runs after save."""
    # GIVEN a model with an after_save hook
    call_order = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @after_save
        def notify(self):
            call_order.append("after_save")

    User._client_instance = None

    user = User(pk="USER#1")

    # WHEN we save
    await user.save()

    # THEN after_save should have been called
    assert "after_save" in call_order


@pytest.mark.asyncio
async def test_skip_hooks_on_save(mock_client):
    """Test that skip_hooks=True skips hooks."""
    # GIVEN a model with a before_save hook
    hook_called = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    User._client_instance = None

    user = User(pk="USER#1")

    # WHEN we save with skip_hooks=True
    await user.save(skip_hooks=True)

    # THEN hook should not be called, but save should happen
    assert len(hook_called) == 0
    mock_client.put_item.assert_called_once()


@pytest.mark.asyncio
async def test_model_config_skip_hooks_default(mock_client):
    """Test that model_config.skip_hooks=True skips hooks by default."""
    # GIVEN a model with skip_hooks=True in config
    hook_called = []

    class BulkModel(Model):
        model_config = ModelConfig(table="bulk", client=mock_client, skip_hooks=True)
        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    BulkModel._client_instance = None

    item = BulkModel(pk="ITEM#1")

    # WHEN we save without specifying skip_hooks
    await item.save()

    # THEN hook should not be called
    assert len(hook_called) == 0


@pytest.mark.asyncio
async def test_model_config_skip_hooks_override(mock_client):
    """Test that skip_hooks=False overrides model_config.skip_hooks=True."""
    # GIVEN a model with skip_hooks=True in config
    hook_called = []

    class BulkModel(Model):
        model_config = ModelConfig(table="bulk", client=mock_client, skip_hooks=True)
        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    BulkModel._client_instance = None

    item = BulkModel(pk="ITEM#1")

    # WHEN we save with skip_hooks=False
    await item.save(skip_hooks=False)

    # THEN hook should be called
    assert len(hook_called) == 1


@pytest.mark.asyncio
async def test_before_delete_hook_runs(mock_client):
    """Test that before_delete hook runs."""
    # GIVEN a model with a before_delete hook
    hook_called = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_delete
        def check_can_delete(self):
            hook_called.append("before_delete")

    User._client_instance = None

    user = User(pk="USER#1")

    # WHEN we delete
    await user.delete()

    # THEN before_delete should have been called
    assert "before_delete" in hook_called


@pytest.mark.asyncio
async def test_before_update_hook_runs(mock_client):
    """Test that before_update hook runs."""
    # GIVEN a model with a before_update hook
    hook_called = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

        @before_update
        def validate_update(self):
            hook_called.append("before_update")

    User._client_instance = None

    user = User(pk="USER#1", name="John")

    # WHEN we update
    await user.update(name="Jane")

    # THEN before_update should have been called
    assert "before_update" in hook_called


@pytest.mark.asyncio
async def test_hook_can_raise_exception(mock_client):
    """Test that hooks can raise exceptions to stop operation."""

    # GIVEN a model with a validating hook that raises on invalid email
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        email = StringAttribute()

        @before_save
        def validate_email(self):
            if not self.email.endswith("@company.com"):
                raise ValueError("Invalid email domain")

    User._client_instance = None

    user = User(pk="USER#1", email="test@gmail.com")

    # WHEN we try to save with invalid email
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Invalid email domain"):
        await user.save()

    # AND put_item should not be called
    mock_client.put_item.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_hooks_run_in_order(mock_client):
    """Test that multiple hooks run in definition order."""
    # GIVEN a model with multiple before_save hooks
    call_order = []

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)

        @before_save
        def first_hook(self):
            call_order.append("first")

        @before_save
        def second_hook(self):
            call_order.append("second")

    User._client_instance = None

    user = User(pk="USER#1")

    # WHEN we save
    await user.save()

    # THEN hooks should run in definition order
    assert call_order == ["first", "second"]
