"""Integration tests for conditions with real DynamoDB operations."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
)


@pytest.fixture
def user_model(dynamo):
    """Create User model for testing."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()
        status = StringAttribute()
        tags = ListAttribute()
        address = MapAttribute()

    User._client_instance = None
    return User


@pytest.mark.asyncio
async def test_save_with_does_not_exist_condition_succeeds(user_model):
    """First save with does_not_exist should work."""
    User = user_model

    # GIVEN a new user
    user = User(pk="COND#1", sk="PROFILE", name="Alice", age=25, status="active")

    # WHEN we save with does_not_exist condition
    await user.save(condition=User.pk.not_exists())

    # THEN the save succeeds
    loaded = await User.get(pk="COND#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "Alice"


@pytest.mark.asyncio
async def test_save_with_does_not_exist_condition_fails_on_existing(user_model):
    """Second save with does_not_exist should fail."""
    User = user_model

    # GIVEN an existing user
    user = User(pk="COND#2", sk="PROFILE", name="Bob", age=30, status="active")
    await user.save()

    # WHEN we try to save another with same key and does_not_exist condition
    user2 = User(pk="COND#2", sk="PROFILE", name="Bob2", age=35, status="active")

    # THEN it fails
    with pytest.raises(Exception) as exc_info:
        await user2.save(condition=User.pk.not_exists())

    assert "condition" in str(exc_info.value).lower() or "Condition" in str(
        type(exc_info.value).__name__
    )


@pytest.mark.asyncio
async def test_save_with_eq_condition_succeeds(user_model):
    """Save with matching == condition should work."""
    User = user_model

    user = User(pk="COND#3", sk="PROFILE", name="Charlie", age=25, status="active")
    await user.save()

    # Update with matching condition
    user.name = "Charlie Updated"
    await user.save(condition=User.status == "active")

    loaded = await User.get(pk="COND#3", sk="PROFILE")
    assert loaded.name == "Charlie Updated"


@pytest.mark.asyncio
async def test_save_with_eq_condition_fails_on_mismatch(user_model):
    """Save with non-matching == condition should fail."""
    User = user_model

    user = User(pk="COND#4", sk="PROFILE", name="Diana", age=25, status="active")
    await user.save()

    user.name = "Diana Updated"
    with pytest.raises(Exception):
        await user.save(condition=User.status == "inactive")

    # Original should be unchanged
    loaded = await User.get(pk="COND#4", sk="PROFILE")
    assert loaded.name == "Diana"


@pytest.mark.asyncio
async def test_delete_with_condition_succeeds(user_model):
    """Delete with matching condition should work."""
    User = user_model

    # GIVEN an active user
    user = User(pk="COND#5", sk="PROFILE", name="Eve", age=25, status="active")
    await user.save()

    # WHEN we delete with matching condition
    await user.delete(condition=User.status == "active")

    # THEN the user is deleted
    loaded = await User.get(pk="COND#5", sk="PROFILE")
    assert loaded is None


@pytest.mark.asyncio
async def test_delete_with_condition_fails_on_mismatch(user_model):
    """Delete with non-matching condition should fail."""
    User = user_model

    # GIVEN an active user
    user = User(pk="COND#6", sk="PROFILE", name="Frank", age=25, status="active")
    await user.save()

    # WHEN we try to delete with wrong condition
    # THEN it fails
    with pytest.raises(Exception):
        await user.delete(condition=User.status == "inactive")

    # AND user is NOT deleted
    loaded = await User.get(pk="COND#6", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "Frank"


@pytest.mark.asyncio
async def test_save_with_combined_condition(user_model):
    """Save with AND condition should work."""
    User = user_model

    user = User(pk="COND#7", sk="PROFILE", name="Grace", age=25, status="active")
    await user.save()

    user.name = "Grace Updated"
    await user.save(condition=(User.status == "active") & (User.age == 25))

    loaded = await User.get(pk="COND#7", sk="PROFILE")
    assert loaded.name == "Grace Updated"


@pytest.mark.asyncio
async def test_save_with_exists_condition(user_model):
    """Save with exists() condition should work."""
    User = user_model

    user = User(pk="COND#8", sk="PROFILE", name="Henry", age=25, status="active")
    await user.save()

    user.name = "Henry Updated"
    await user.save(condition=User.name.exists())

    loaded = await User.get(pk="COND#8", sk="PROFILE")
    assert loaded.name == "Henry Updated"


@pytest.mark.asyncio
async def test_delete_with_gt_condition(user_model):
    """Delete with > condition should work."""
    User = user_model

    user = User(pk="COND#9", sk="PROFILE", name="Ivy", age=30, status="active")
    await user.save()

    await user.delete(condition=User.age > 25)

    loaded = await User.get(pk="COND#9", sk="PROFILE")
    assert loaded is None


@pytest.mark.asyncio
async def test_save_with_or_condition(user_model):
    """Save with OR condition should work."""
    User = user_model

    user = User(pk="COND#10", sk="PROFILE", name="Jack", age=25, status="pending")
    await user.save()

    # Update if status is active OR pending
    user.name = "Jack Updated"
    await user.save(condition=(User.status == "active") | (User.status == "pending"))

    loaded = await User.get(pk="COND#10", sk="PROFILE")
    assert loaded.name == "Jack Updated"


@pytest.mark.asyncio
async def test_save_with_not_condition(user_model):
    """Save with NOT condition should work."""
    User = user_model

    user = User(pk="COND#11", sk="PROFILE", name="Kate", age=25, status="active")
    await user.save()

    # Update if status is NOT deleted
    user.name = "Kate Updated"
    await user.save(condition=~(User.status == "deleted"))

    loaded = await User.get(pk="COND#11", sk="PROFILE")
    assert loaded.name == "Kate Updated"


@pytest.mark.asyncio
async def test_save_with_complex_condition(user_model):
    """Save with complex AND/OR/NOT condition should work."""
    User = user_model

    user = User(pk="COND#12", sk="PROFILE", name="Leo", age=30, status="active")
    await user.save()

    # Complex: (status == active AND age > 25) OR name exists
    complex_cond = ((User.status == "active") & (User.age > 25)) | User.name.exists()

    user.name = "Leo Updated"
    await user.save(condition=complex_cond)

    loaded = await User.get(pk="COND#12", sk="PROFILE")
    assert loaded.name == "Leo Updated"


@pytest.mark.asyncio
async def test_delete_with_or_condition(user_model):
    """Delete with OR condition should work."""
    User = user_model

    user = User(pk="COND#13", sk="PROFILE", name="Mia", age=25, status="inactive")
    await user.save()

    # Delete if status is active OR inactive
    await user.delete(condition=(User.status == "active") | (User.status == "inactive"))

    loaded = await User.get(pk="COND#13", sk="PROFILE")
    assert loaded is None


@pytest.mark.asyncio
async def test_save_with_between_condition(user_model):
    """Save with between condition should work."""
    User = user_model

    user = User(pk="COND#14", sk="PROFILE", name="Nina", age=30, status="active")
    await user.save()

    user.name = "Nina Updated"
    await user.save(condition=User.age.between(25, 35))

    loaded = await User.get(pk="COND#14", sk="PROFILE")
    assert loaded.name == "Nina Updated"


@pytest.mark.asyncio
async def test_save_with_begins_with_condition(user_model):
    """Save with begins_with condition should work."""
    User = user_model

    user = User(pk="COND#15", sk="ORDER#001", name="Oscar", age=25, status="active")
    await user.save()

    user.name = "Oscar Updated"
    await user.save(condition=User.sk.begins_with("ORDER#"))

    loaded = await User.get(pk="COND#15", sk="ORDER#001")
    assert loaded.name == "Oscar Updated"


@pytest.mark.asyncio
async def test_save_with_condition_in_variable(user_model):
    """Save with condition stored in variable should work."""
    User = user_model

    user = User(pk="COND#16", sk="PROFILE", name="Paul", age=28, status="active")
    await user.save()

    # Build condition and store in variable
    is_active = User.status == "active"
    is_adult = User.age >= 18
    my_condition = is_active & is_adult

    user.name = "Paul Updated"
    await user.save(condition=my_condition)

    loaded = await User.get(pk="COND#16", sk="PROFILE")
    assert loaded.name == "Paul Updated"


@pytest.mark.asyncio
async def test_delete_with_condition_in_variable(user_model):
    """Delete with condition stored in variable should work."""
    User = user_model

    user = User(pk="COND#17", sk="PROFILE", name="Quinn", age=35, status="pending")
    await user.save()

    # Build complex condition in steps
    status_ok = (User.status == "active") | (User.status == "pending")
    age_ok = User.age > 30
    final_condition = status_ok & age_ok

    await user.delete(condition=final_condition)

    loaded = await User.get(pk="COND#17", sk="PROFILE")
    assert loaded is None


@pytest.mark.asyncio
async def test_reuse_condition_multiple_times(user_model):
    """Same condition can be reused for multiple operations."""
    User = user_model

    # Create two users
    user1 = User(pk="COND#18", sk="PROFILE", name="Rose", age=25, status="active")
    await user1.save()
    user2 = User(pk="COND#19", sk="PROFILE", name="Sam", age=30, status="active")
    await user2.save()

    # Define condition once, use twice
    must_be_active = User.status == "active"

    user1.name = "Rose Updated"
    await user1.save(condition=must_be_active)

    user2.name = "Sam Updated"
    await user2.save(condition=must_be_active)

    loaded1 = await User.get(pk="COND#18", sk="PROFILE")
    loaded2 = await User.get(pk="COND#19", sk="PROFILE")
    assert loaded1.name == "Rose Updated"
    assert loaded2.name == "Sam Updated"
