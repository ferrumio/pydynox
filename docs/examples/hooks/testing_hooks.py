"""Testing lifecycle hooks with pydynox_memory_backend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.hooks import after_save, before_save


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    email = StringAttribute()
    name = StringAttribute()

    @before_save
    def validate_email(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email")

    @before_save
    def normalize_email(self):
        if self.email:
            self.email = self.email.lower().strip()

    @after_save
    def log_save(self):
        print(f"Saved user: {self.pk}")


@pytest.mark.asyncio
async def test_before_save_validation(pydynox_memory_backend):
    """Test that before_save hook validates data."""
    user = User(pk="USER#1", email="invalid-email", name="John")

    with pytest.raises(ValueError, match="Invalid email"):
        await user.save()

    # User was not saved
    assert await User.get(pk="USER#1") is None


@pytest.mark.asyncio
async def test_before_save_normalization(pydynox_memory_backend):
    """Test that before_save hook normalizes data."""
    user = User(pk="USER#1", email="  JOHN@EXAMPLE.COM  ", name="John")
    await user.save()

    found = await User.get(pk="USER#1")
    assert found is not None
    assert found.email == "john@example.com"


@pytest.mark.asyncio
async def test_skip_hooks(pydynox_memory_backend):
    """Test skipping hooks for special cases."""
    # This would normally fail validation
    user = User(pk="USER#1", email="invalid", name="John")
    await user.save(skip_hooks=True)

    # But with skip_hooks=True, it saves anyway
    found = await User.get(pk="USER#1")
    assert found is not None
    assert found.email == "invalid"
