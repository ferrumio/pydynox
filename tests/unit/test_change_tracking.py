"""Unit tests for change tracking (smart updates)."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    email = StringAttribute()
    age = NumberAttribute()


def test_new_instance_not_dirty():
    """New instance should not be dirty."""
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    assert user.is_dirty is False
    assert user.changed_fields == []


def test_new_instance_has_no_original():
    """New instance should have no original snapshot."""
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    assert user._original is None


def test_from_dict_stores_original():
    """from_dict should store original values for change tracking."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    assert user._original is not None
    assert user._original == data
    assert user.is_dirty is False


def test_change_marks_dirty():
    """Changing an attribute should mark the instance as dirty."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user.name = "Jane"

    assert user.is_dirty is True
    assert "name" in user.changed_fields


def test_multiple_changes_tracked():
    """Multiple changes should all be tracked."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user.name = "Jane"
    user.email = "jane@example.com"

    assert user.is_dirty is True
    assert set(user.changed_fields) == {"name", "email"}


def test_revert_to_original_clears_dirty():
    """Setting value back to original should clear dirty flag for that field."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user.name = "Jane"
    assert "name" in user.changed_fields

    user.name = "John"  # Back to original
    assert "name" not in user.changed_fields


def test_change_key_tracked():
    """Changing partition key should be tracked."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user.pk = "USER#2"
    assert "pk" in user.changed_fields


def test_internal_attrs_not_tracked():
    """Internal attributes (starting with _) should not be tracked."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user._some_internal = "value"
    assert user.is_dirty is False


def test_reset_change_tracking():
    """_reset_change_tracking should clear changes and update original."""
    data = {"pk": "USER#1", "name": "John", "email": "john@example.com", "age": 30}
    user = User.from_dict(data)

    user.name = "Jane"
    assert user.is_dirty is True

    user._reset_change_tracking()

    assert user.is_dirty is False
    assert user.changed_fields == []
    assert user._original["name"] == "Jane"


@MemoryBackend()
def test_save_resets_tracking_sync():
    """sync_save() should reset change tracking after successful save."""
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    user.sync_save()

    # After save, original should be set
    assert user._original is not None
    assert user.is_dirty is False

    # Make a change
    user.name = "Jane"
    assert user.is_dirty is True

    # Save again
    user.sync_save()

    # Should be clean again
    assert user.is_dirty is False
    assert user._original["name"] == "Jane"


@MemoryBackend()
def test_get_returns_clean_instance():
    """get() should return a clean instance with original set."""
    # Save a user
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    user.sync_save()

    # Get it back
    loaded = User.sync_get(pk="USER#1")

    assert loaded is not None
    assert loaded._original is not None
    assert loaded.is_dirty is False


@MemoryBackend()
def test_smart_save_only_updates_changed():
    """Smart save should only update changed fields."""
    # Save initial user
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    user.sync_save()

    # Load and modify
    loaded = User.sync_get(pk="USER#1")
    loaded.name = "Jane"

    # Save - should use UpdateItem with only 'name'
    loaded.sync_save()

    # Verify the update worked
    result = User.sync_get(pk="USER#1")
    assert result.name == "Jane"
    assert result.email == "john@example.com"  # Unchanged
    assert result.age == 30  # Unchanged


@MemoryBackend()
def test_full_replace_uses_putitem():
    """full_replace=True should use PutItem with all fields."""
    # Save initial user
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    user.sync_save()

    # Load and modify
    loaded = User.sync_get(pk="USER#1")
    loaded.name = "Jane"

    # Save with full_replace
    loaded.sync_save(full_replace=True)

    # Verify the update worked
    result = User.sync_get(pk="USER#1")
    assert result.name == "Jane"


@MemoryBackend()
def test_new_item_uses_putitem():
    """New items (no original) should always use PutItem."""
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)

    # No original means PutItem
    assert user._original is None

    user.sync_save()

    # After save, original is set
    assert user._original is not None


@MemoryBackend()
def test_no_changes_still_saves():
    """If no changes, save should still work (uses PutItem)."""
    user = User(pk="USER#1", name="John", email="john@example.com", age=30)
    user.sync_save()

    # Load but don't change anything
    loaded = User.sync_get(pk="USER#1")
    assert loaded.is_dirty is False

    # Save anyway - should use PutItem since no changes
    loaded.sync_save()

    # Should still work
    result = User.sync_get(pk="USER#1")
    assert result.name == "John"
