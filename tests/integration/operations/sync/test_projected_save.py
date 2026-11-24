"""Integration tests for models loaded with a projection (sync)."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException

LOADERS = ["batch_get", "query", "scan"]


def _store_account(dynamo):
    item = {
        "pk": f"SPROJSAVE#{uuid.uuid4().hex}",
        "sk": "ACCOUNT",
        "tags": ["a"],
        "prefs": {"theme": "dark"},
        "labels": {"x"},
        "details": {"zip": "123"},
        "name": "Ann",
        "legacy": "keep",
    }
    dynamo.sync_put_item("test_table", item)
    return item


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


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_model_saves_in_place_changes(dynamo, account_cls, how):
    # GIVEN an account loaded with a projection
    item = _store_account(dynamo)
    key = {"pk": item["pk"], "sk": item["sk"]}
    account = _load(account_cls, how, item, ["pk", "sk", "tags", "prefs", "labels"])

    # WHEN changing the fetched collections in place
    account.tags.append("b")
    account.prefs["theme"] = "light"
    account.labels.add("y")
    account.sync_save()

    # THEN the changes are stored and the other fields are kept
    stored = dynamo.sync_get_item("test_table", key)
    assert stored["tags"] == ["a", "b"]
    assert stored["prefs"] == {"theme": "light"}
    assert set(stored["labels"]) == {"x", "y"}
    assert stored["details"] == {"zip": "123"}
    assert stored["name"] == "Ann"


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_model_checks_condition_without_changes(dynamo, user_cls, how):
    # GIVEN a user loaded with a projection and no changes
    item = _store(dynamo)
    key = {"pk": item["pk"], "sk": item["sk"]}
    user = _load(user_cls, how, item, ["pk", "sk", "name"])

    # WHEN saving with a condition that is false
    # THEN it raises and the item is untouched
    with pytest.raises(ConditionalCheckFailedException):
        user.sync_save(condition=user_cls.name == "Bob")
    assert dynamo.sync_get_item("test_table", key) == item

    # AND a true condition saves without changing the item
    user.sync_save(condition=user_cls.name == "Ann")
    assert dynamo.sync_get_item("test_table", key) == item


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_read_calls_custom_from_dict(dynamo, how):
    # GIVEN a model that overrides from_dict
    seen = []

    class Custom(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute(required=True)
        age = NumberAttribute(default=0)

        @classmethod
        def from_dict(cls, data):
            seen.append(dict(data))
            return super().from_dict(data)

    item = _store(dynamo)

    # WHEN loading it with a projection
    custom = _load(Custom, how, item, ["pk", "sk", "name"])

    # THEN the override ran and the model is projected
    assert len(seen) == 1
    assert custom.age is None


@pytest.mark.parametrize("how", LOADERS)
def test_sync_projected_model_refuses_missing_nested_field(dynamo, account_cls, how):
    # GIVEN details holds zip and the projection asks for a missing nested path
    item = _store_account(dynamo)
    key = {"pk": item["pk"], "sk": item["sk"]}
    account = _load(account_cls, how, item, ["pk", "sk", "details.city"])

    # WHEN replacing details and saving
    account.details = {"city": "new"}

    # THEN it raises instead of deleting zip
    with pytest.raises(ValueError, match="nested projection"):
        account.sync_save()
    assert dynamo.sync_get_item("test_table", key)["details"] == {"zip": "123"}


@pytest.mark.parametrize("how", LOADERS)
def test_sync_second_save_keeps_attributes_outside_the_schema(dynamo, account_cls, how):
    # GIVEN an item with an attribute the model does not declare
    item = _store_account(dynamo)
    key = {"pk": item["pk"], "sk": item["sk"]}
    account = _load(account_cls, how, item, ["pk", "sk"])

    # WHEN saving every field that was not fetched, then saving again
    account.tags = ["t"]
    account.prefs = {"theme": "x"}
    account.labels = {"z"}
    account.details = {"zip": "9"}
    account.name = "Bob"
    account.sync_save()
    account.sync_save()

    # THEN the attribute outside the schema is still stored
    assert dynamo.sync_get_item("test_table", key)["legacy"] == "keep"
