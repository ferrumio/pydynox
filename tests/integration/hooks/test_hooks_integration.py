"""Integration tests for lifecycle hooks with real DynamoDB operations."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.hooks import after_delete, after_save, before_delete, before_save


def test_hooks_run_on_save(dynamo):
    """Test that hooks run when saving to real DynamoDB."""
    # GIVEN a model with before_save and after_save hooks
    call_log = []

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def log_before_save(self):
            call_log.append(f"before_save:{self.pk}")

        @after_save
        def log_after_save(self):
            call_log.append(f"after_save:{self.pk}")

    User._client_instance = None
    user = User(pk="USER#1", sk="PROFILE", name="John")

    # WHEN saving the user
    user.save()

    # THEN both hooks are called and item is saved
    assert "before_save:USER#1" in call_log
    assert "after_save:USER#1" in call_log
    loaded = User.get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "John"


def test_hooks_run_on_delete(dynamo):
    """Test that hooks run when deleting from real DynamoDB."""
    # GIVEN a saved user with delete hooks
    call_log = []

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_delete
        def log_before_delete(self):
            call_log.append(f"before_delete:{self.pk}")

        @after_delete
        def log_after_delete(self):
            call_log.append(f"after_delete:{self.pk}")

    User._client_instance = None
    user = User(pk="USER#2", sk="PROFILE", name="Jane")
    user.save()
    call_log.clear()

    # WHEN deleting the user
    user.delete()

    # THEN both hooks are called and item is deleted
    assert "before_delete:USER#2" in call_log
    assert "after_delete:USER#2" in call_log
    loaded = User.get(pk="USER#2", sk="PROFILE")
    assert loaded is None


def test_skip_hooks_on_save(dynamo):
    """Test that skip_hooks=True skips hooks on real save."""
    # GIVEN a model with a before_save hook
    hook_called = []

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def validate(self):
            hook_called.append("called")

    User._client_instance = None
    user = User(pk="USER#3", sk="PROFILE", name="Bob")

    # WHEN saving with skip_hooks=True
    user.save(skip_hooks=True)

    # THEN hook is not called but item is saved
    assert len(hook_called) == 0
    loaded = User.get(pk="USER#3", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "Bob"


def test_before_save_validation_blocks_save(dynamo):
    """Test that before_save can block save with exception."""

    # GIVEN a model with email validation in before_save
    class ValidatedUser(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()

        @before_save
        def validate_email(self):
            if not self.email.endswith("@company.com"):
                raise ValueError("Email must be @company.com")

    ValidatedUser._client_instance = None
    user = ValidatedUser(pk="USER#4", sk="PROFILE", email="test@gmail.com")

    # WHEN saving with invalid email
    # THEN ValueError is raised and item is not saved
    with pytest.raises(ValueError, match="Email must be @company.com"):
        user.save()

    loaded = ValidatedUser.get(pk="USER#4", sk="PROFILE")
    assert loaded is None


def test_before_save_can_modify_data(dynamo):
    """Test that before_save can modify data before saving."""

    # GIVEN a model that normalizes name in before_save
    class NormalizedUser(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

        @before_save
        def normalize_name(self):
            self.name = self.name.strip().title()

    NormalizedUser._client_instance = None
    user = NormalizedUser(pk="USER#5", sk="PROFILE", name="  john doe  ")

    # WHEN saving
    user.save()

    # THEN name is normalized locally and in DynamoDB
    assert user.name == "John Doe"
    loaded = NormalizedUser.get(pk="USER#5", sk="PROFILE")
    assert loaded.name == "John Doe"


def test_model_config_skip_hooks_default(dynamo):
    """Test that model_config.skip_hooks=True skips hooks by default."""
    # GIVEN a model with skip_hooks=True in config
    call_log = []

    class BulkModel(Model):
        model_config = ModelConfig(table="test_table", client=dynamo, skip_hooks=True)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

        @before_save
        def log_save(self):
            call_log.append("called")

    BulkModel._client_instance = None
    item = BulkModel(pk="BULK#1", sk="DATA")

    # WHEN saving without explicit skip_hooks
    item.save()

    # THEN hook is not called but item is saved
    assert len(call_log) == 0
    loaded = BulkModel.get(pk="BULK#1", sk="DATA")
    assert loaded is not None


def test_model_config_skip_hooks_override(dynamo):
    """Test that skip_hooks=False overrides model_config.skip_hooks=True."""
    # GIVEN a model with skip_hooks=True in config
    call_log = []

    class BulkModel(Model):
        model_config = ModelConfig(table="test_table", client=dynamo, skip_hooks=True)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

        @before_save
        def log_save(self):
            call_log.append("called")

    BulkModel._client_instance = None
    item = BulkModel(pk="BULK#2", sk="DATA")

    # WHEN saving with skip_hooks=False
    item.save(skip_hooks=False)

    # THEN hook is called
    assert len(call_log) == 1
