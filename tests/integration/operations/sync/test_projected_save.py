"""Integration tests for models loaded with a projection (sync)."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

LOADERS = ["batch_get", "query", "scan"]


@pytest.fixture
def user_cls(dynamo):
    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute(required=True)
        age = NumberAttribute(default=0)
        email = StringAttribute()

    return User


def _store(dynamo):
    item = {
        "pk": f"SPROJSAVE#{uuid.uuid4().hex}",
        "sk": "PROFILE",
        "name": "Ann",
        "age": 42,
        "email": "ann@example.com",
    }
    dynamo.sync_put_item("test_table", item)
    return item


def _load(user_cls, how, item, fields):
    if how == "batch_get":
        key = {"pk": item["pk"], "sk": item["sk"]}
        return user_cls.sync_batch_get([key], projection=fields)[0]
    if how == "query":
        return user_cls.sync_query(partition_key=item["pk"], fields=fields).first()
    users = list(
        user_cls.sync_scan(
            filter_condition=user_cls.pk == item["pk"], fields=fields, consistent_read=True
        )
    )
    return users[0]


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_model_leaves_fields_not_fetched_as_none(dynamo, user_cls, how):
    # GIVEN a stored user whose age differs from the default
    item = _store(dynamo)

    # WHEN loading without age, email, or the required name
    user = _load(user_cls, how, item, ["pk", "sk"])

    # THEN those fields are None, with no default or required error
    assert user.pk == item["pk"]
    assert user.name is None
    assert user.age is None
    assert user.email is None


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_model_save_keeps_fields_not_fetched(dynamo, user_cls, how):
    # GIVEN a user loaded with a projection
    item = _store(dynamo)
    key = {"pk": item["pk"], "sk": item["sk"]}
    user = _load(user_cls, how, item, ["pk", "sk", "name"])

    # WHEN saving it without changes
    user.sync_save()

    # THEN the stored item is unchanged
    assert dynamo.sync_get_item("test_table", key) == item

    # WHEN saving a change to one field
    user.name = "Bob"
    user.sync_save()

    # THEN only that field changes
    assert dynamo.sync_get_item("test_table", key) == {**item, "name": "Bob"}


def test_sync_new_model_still_validates(user_cls):
    # GIVEN a model class with a required field and a default
    # WHEN creating a new model without the required field
    # THEN it still fails
    with pytest.raises(ValueError, match="'name' is required"):
        user_cls(pk="SPROJSAVE#new", sk="PROFILE")

    # AND defaults still apply
    assert user_cls(pk="SPROJSAVE#new", sk="PROFILE", name="Ann").age == 0
