"""Strict models still read partial schemas and update declared fields."""

from uuid import uuid4

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


@pytest.fixture
def strict_user(dynamo):
    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo, strict_attributes=True)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute(alias="n")

    key = {"pk": f"strict-{uuid4()}", "sk": "PROFILE"}
    dynamo.sync_put_item("test_table", {**key, "n": "Alice", "future_field": "keep"})
    yield User, key
    dynamo.sync_delete_item("test_table", key)


@pytest.mark.parametrize("mode", ["async", "sync"])
async def test_strict_model_reads_extra_fields_and_saves_changes(strict_user, dynamo, mode):
    # GIVEN a stored item that has a field outside the strict model's schema
    User, key = strict_user

    # WHEN reading with individual, batch, and paginated APIs
    if mode == "async":
        user = await User.get(**key)
        batches = await User.batch_get([key])
        query = [item async for item in User.query(key["pk"], page_size=1)]
        scan = [item async for item in User.scan(filter_condition=User.pk == key["pk"])]
        raw = await User.get(**key, as_dict=True)
    else:
        user = User.sync_get(**key)
        batches = User.sync_batch_get([key])
        query = list(User.sync_query(key["pk"], page_size=1))
        scan = list(User.sync_scan(filter_condition=User.pk == key["pk"]))
        raw = User.sync_get(**key, as_dict=True)

    # THEN extra fields are ignored in models and kept in raw results
    for results in ([user], batches, query, scan):
        assert len(results) == 1
        loaded = results[0]
        assert loaded.name == "Alice"
        assert not hasattr(loaded, "future_field")
        assert not loaded.is_dirty
        with pytest.raises(AttributeError, match="User has no attribute 'naem'"):
            loaded.naem = "Bob"
    assert raw["future_field"] == "keep"

    # WHEN changing a declared field and saving
    user.name = "Bob"
    user._cache = {"request": "123"}
    if mode == "async":
        await user.save()
        stored = await dynamo.get_item("test_table", key)
    else:
        user.sync_save()
        stored = dynamo.sync_get_item("test_table", key)

    # THEN the aliased field is updated and the stored extra field is untouched
    assert stored == {**key, "n": "Bob", "future_field": "keep"}
    assert not user.is_dirty

    # WHEN using the explicit update API
    if mode == "async":
        await user.update(name="Charlie")
        reloaded = await User.get(**key)
    else:
        user.sync_update(name="Charlie")
        reloaded = User.sync_get(**key)

    # THEN the strict model still loads the updated item
    assert reloaded.name == "Charlie"
    assert not reloaded.is_dirty
