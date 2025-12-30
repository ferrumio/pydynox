"""Integration tests for lifecycle hooks with real DynamoDB operations."""

import pytest
from pydynox import Model
from pydynox.attributes import StringAttribute
from pydynox.hooks import after_delete, after_save, before_delete, before_save


def test_hooks_run_on_save(dynamo):
    """Test that hooks run when saving to real DynamoDB."""
    call_log = []

    class User(Model):
        class Meta:
            table = "test_table"

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def log_before_save(self):
            call_log.append(f"before_save:{self.pk}")

        @after_save
        def log_after_save(self):
            call_log.append(f"after_save:{self.pk}")

    User._client = dynamo

    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.save()

    assert "before_save:USER#1" in call_log
    assert "after_save:USER#1" in call_log

    # Verify item was saved
    loaded = User.get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "John"


def test_hooks_run_on_delete(dynamo):
    """Test that hooks run when deleting from real DynamoDB."""
    call_log = []

    class User(Model):
        class Meta:
            table = "test_table"

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_delete
        def log_before_delete(self):
            call_log.append(f"before_delete:{self.pk}")

        @after_delete
        def log_after_delete(self):
            call_log.append(f"after_delete:{self.pk}")

    User._client = dynamo

    user = User(pk="USER#2", sk="PROFILE", name="Jane")
    user.save()
    call_log.clear()

    user.delete()

    assert "before_delete:USER#2" in call_log
    assert "after_delete:USER#2" in call_log

    # Verify item was deleted
    loaded = User.get(pk="USER#2", sk="PROFILE")
    assert loaded is None


def test_skip_hooks_on_save(dynamo):
    """Test that skip_hooks=True skips hooks on real save."""
    hook_called = []

    class User(Model):
        class Meta:
            table = "test_table"

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def validate(self):
            hook_called.append("called")

    User._client = dynamo

    user = User(pk="USER#3", sk="PROFILE", name="Bob")
    user.save(skip_hooks=True)

    assert len(hook_called) == 0

    # But item should still be saved
    loaded = User.get(pk="USER#3", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "Bob"


def test_before_save_validation_blocks_save(dynamo):
    """Test that before_save can block save with exception."""

    class ValidatedUser(Model):
        class Meta:
            table = "test_table"

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()

        @before_save
        def validate_email(self):
            if not self.email.endswith("@company.com"):
                raise ValueError("Email must be @company.com")

    ValidatedUser._client = dynamo

    user = ValidatedUser(pk="USER#4", sk="PROFILE", email="test@gmail.com")

    with pytest.raises(ValueError, match="Email must be @company.com"):
        user.save()

    # Item should NOT be saved
    loaded = ValidatedUser.get(pk="USER#4", sk="PROFILE")
    assert loaded is None


def test_before_save_can_modify_data(dynamo):
    """Test that before_save can modify data before saving."""

    class NormalizedUser(Model):
        class Meta:
            table = "test_table"

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def normalize_name(self):
            self.name = self.name.strip().title()

    NormalizedUser._client = dynamo

    user = NormalizedUser(pk="USER#5", sk="PROFILE", name="  john doe  ")
    user.save()

    # Local instance should be modified
    assert user.name == "John Doe"

    # Saved data should be normalized
    loaded = NormalizedUser.get(pk="USER#5", sk="PROFILE")
    assert loaded.name == "John Doe"


def test_meta_skip_hooks_default(dynamo):
    """Test that Meta.skip_hooks=True skips hooks by default."""
    call_log = []

    class BulkModel(Model):
        class Meta:
            table = "test_table"
            skip_hooks = True

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

        @before_save
        def log_save(self):
            call_log.append("called")

    BulkModel._client = dynamo

    item = BulkModel(pk="BULK#1", sk="DATA")
    item.save()

    assert len(call_log) == 0

    # But item should be saved
    loaded = BulkModel.get(pk="BULK#1", sk="DATA")
    assert loaded is not None


def test_meta_skip_hooks_override(dynamo):
    """Test that skip_hooks=False overrides Meta.skip_hooks=True."""
    call_log = []

    class BulkModel(Model):
        class Meta:
            table = "test_table"
            skip_hooks = True

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

        @before_save
        def log_save(self):
            call_log.append("called")

    BulkModel._client = dynamo

    item = BulkModel(pk="BULK#2", sk="DATA")
    item.save(skip_hooks=False)

    assert len(call_log) == 1
