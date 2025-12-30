"""Tests for lifecycle hooks."""

from unittest.mock import MagicMock

import pytest
from pydynox import Model
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


def test_hook_decorator_sets_hook_type():
    """Test that decorators set _hook_type attribute."""

    @before_save
    def my_hook(self):
        pass

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

    @decorator
    def hook(self):
        pass

    assert hook._hook_type == expected_type


def test_model_collects_hooks():
    """Test that Model metaclass collects hooks."""

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            pass

        @after_save
        def notify(self):
            pass

    assert len(User._hooks[HookType.BEFORE_SAVE]) == 1
    assert len(User._hooks[HookType.AFTER_SAVE]) == 1


def test_model_inherits_hooks():
    """Test that hooks are inherited from parent class."""

    class BaseModel(Model):
        class Meta:
            table = "base"

        pk = StringAttribute(hash_key=True)

        @before_save
        def base_validate(self):
            pass

    class User(BaseModel):
        class Meta:
            table = "users"

        @before_save
        def user_validate(self):
            pass

    # Should have both hooks
    assert len(User._hooks[HookType.BEFORE_SAVE]) == 2


def test_before_save_hook_runs():
    """Test that before_save hook runs before save."""
    call_order = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            call_order.append("before_save")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1")
    user.save()

    assert "before_save" in call_order
    mock_client.put_item.assert_called_once()


def test_after_save_hook_runs():
    """Test that after_save hook runs after save."""
    call_order = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @after_save
        def notify(self):
            call_order.append("after_save")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1")
    user.save()

    assert "after_save" in call_order


def test_skip_hooks_on_save():
    """Test that skip_hooks=True skips hooks."""
    hook_called = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1")
    user.save(skip_hooks=True)

    assert len(hook_called) == 0
    mock_client.put_item.assert_called_once()


def test_meta_skip_hooks_default():
    """Test that Meta.skip_hooks=True skips hooks by default."""
    hook_called = []

    class BulkModel(Model):
        class Meta:
            table = "bulk"
            skip_hooks = True

        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    mock_client = MagicMock()
    BulkModel._client = mock_client

    item = BulkModel(pk="ITEM#1")
    item.save()

    assert len(hook_called) == 0


def test_meta_skip_hooks_override():
    """Test that skip_hooks=False overrides Meta.skip_hooks=True."""
    hook_called = []

    class BulkModel(Model):
        class Meta:
            table = "bulk"
            skip_hooks = True

        pk = StringAttribute(hash_key=True)

        @before_save
        def validate(self):
            hook_called.append("called")

    mock_client = MagicMock()
    BulkModel._client = mock_client

    item = BulkModel(pk="ITEM#1")
    item.save(skip_hooks=False)

    assert len(hook_called) == 1


def test_before_delete_hook_runs():
    """Test that before_delete hook runs."""
    hook_called = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @before_delete
        def check_can_delete(self):
            hook_called.append("before_delete")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1")
    user.delete()

    assert "before_delete" in hook_called


def test_before_update_hook_runs():
    """Test that before_update hook runs."""
    hook_called = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

        @before_update
        def validate_update(self):
            hook_called.append("before_update")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1", name="John")
    user.update(name="Jane")

    assert "before_update" in hook_called


def test_hook_can_raise_exception():
    """Test that hooks can raise exceptions to stop operation."""

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)
        email = StringAttribute()

        @before_save
        def validate_email(self):
            if not self.email.endswith("@company.com"):
                raise ValueError("Invalid email domain")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1", email="test@gmail.com")

    with pytest.raises(ValueError, match="Invalid email domain"):
        user.save()

    # put_item should not be called
    mock_client.put_item.assert_not_called()


def test_multiple_hooks_run_in_order():
    """Test that multiple hooks run in definition order."""
    call_order = []

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

        @before_save
        def first_hook(self):
            call_order.append("first")

        @before_save
        def second_hook(self):
            call_order.append("second")

    mock_client = MagicMock()
    User._client = mock_client

    user = User(pk="USER#1")
    user.save()

    assert call_order == ["first", "second"]
