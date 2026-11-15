"""Unit tests for models loaded with a projection (batch_get, query, scan)."""

from typing import Any

import pytest
from pydynox import AutoGenerate, Model, ModelConfig, SyncTransaction, Transaction
from pydynox.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
    StringSetAttribute,
    VersionAttribute,
)
from pydynox.exceptions import ConditionalCheckFailedException
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute(required=True)
    age = NumberAttribute(default=0)
    email = StringAttribute()


STORED = {"pk": "USER#1", "name": "Ann", "age": 42, "email": "ann@example.com"}

LOADERS = ["batch_get", "query", "scan"]
MODES = [False, True]


async def _load(model: Any, how: str, sync: bool, fields: list[str], pk: str = "USER#1") -> Any:
    """Load one model through batch_get, query, or scan with a projection."""
    if how == "batch_get":
        if sync:
            return model.sync_batch_get([{"pk": pk}], projection=fields)[0]
        return (await model.batch_get([{"pk": pk}], projection=fields))[0]
    if how == "query":
        if sync:
            return model.sync_query(partition_key=pk, fields=fields).first()
        return await model.query(partition_key=pk, fields=fields).first()
    if sync:
        return model.sync_scan(fields=fields).first()
    return await model.scan(fields=fields).first()


async def _save(instance: Any, sync: bool, **kwargs: Any) -> None:
    if sync:
        instance.sync_save(**kwargs)
    else:
        await instance.save(**kwargs)


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_fields_not_fetched_are_none(how, sync):
    with MemoryBackend():
        # GIVEN a stored user whose age differs from the default
        await User(**STORED).save()

        # WHEN loading only pk and name
        user = await _load(User, how, sync, ["pk", "name"])

        # THEN fields that were not fetched are None, not their default
        assert user.name == "Ann"
        assert user.age is None
        assert user.email is None
        assert not user.is_dirty


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_required_field_not_fetched_does_not_raise(how, sync):
    with MemoryBackend():
        # GIVEN a stored user
        await User(**STORED).save()

        # WHEN loading without the required name
        user = await _load(User, how, sync, ["pk"])

        # THEN the model is created and name is None
        assert user.pk == "USER#1"
        assert user.name is None


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_save_without_changes_keeps_stored_item(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        await User(**STORED).save()
        user = await _load(User, how, sync, ["pk", "name"])

        # WHEN saving it without changes
        await _save(user, sync)

        # THEN the stored item is unchanged
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_save_with_changes_writes_only_changed_fields(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        await User(**STORED).save()
        user = await _load(User, how, sync, ["pk", "name"])

        # WHEN changing a fetched field and a field that was not fetched
        user.name = "Bob"
        user.email = "bob@example.com"
        await _save(user, sync)

        # THEN only those fields change, and age keeps its stored value
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == {
            "pk": "USER#1",
            "name": "Bob",
            "age": 42,
            "email": "bob@example.com",
        }
        assert not user.is_dirty


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_setting_field_not_fetched_to_none_is_a_change(sync):
    with MemoryBackend() as backend:
        # GIVEN a user loaded without email
        await User(**STORED).save()
        user = await _load(User, "query", sync, ["pk", "name"])

        # WHEN setting email to None
        user.email = None

        # THEN it counts as a change, because the stored value is unknown
        assert user.changed_fields == ["email"]
        await _save(user, sync)
        stored = backend.client.sync_get_item("users", {"pk": "USER#1"})
        assert stored is not None
        assert stored.get("email") is None
        assert stored["age"] == 42


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_full_replace_writes_only_fetched_fields(sync):
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        await User(**STORED).save()
        user = await _load(User, "batch_get", sync, ["pk", "name"])

        # WHEN asking for a full replace
        await _save(user, sync, full_replace=True)

        # THEN the item is replaced with the fetched fields only
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == {
            "pk": "USER#1",
            "name": "Ann",
        }


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_without_fetched_key_raises(sync):
    with MemoryBackend() as backend:
        # GIVEN a user loaded without its partition key
        await User(**STORED).save()
        user = await _load(User, "scan", sync, ["name"])

        # WHEN saving it
        # THEN it fails before writing anything
        with pytest.raises(ValueError, match="key attribute 'pk' was not fetched"):
            await _save(user, sync)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED


def test_projection_that_fetches_every_field_is_a_full_load():
    with MemoryBackend():
        # GIVEN a stored user
        User(**STORED).sync_save()

        # WHEN loading every field
        user = User.sync_query(
            partition_key="USER#1", fields=["pk", "name", "age", "email"]
        ).first()

        # THEN the model is not partial
        assert user is not None
        assert not user._is_partial
        assert user.age == 42


def test_fetched_field_missing_from_item_gets_default():
    with MemoryBackend() as backend:
        # GIVEN a stored item without age
        backend.client.sync_put_item("users", {"pk": "USER#1", "name": "Ann"})

        # WHEN loading age with a projection
        user = User.sync_batch_get([{"pk": "USER#1"}], projection=["pk", "name", "age"])[0]

        # THEN age was fetched, so it gets its default like a full read
        assert user.age == 0


def test_constructor_validation_is_unchanged():
    with MemoryBackend():
        # GIVEN a projected read that leaves out the required name
        User(**STORED).sync_save()
        User.sync_batch_get([{"pk": "USER#1"}], projection=["pk"])

        # WHEN creating a new model without name
        # THEN the required check still applies
        with pytest.raises(ValueError, match="'name' is required"):
            User(pk="USER#2")

        # AND a new model still gets its defaults
        assert User(pk="USER#2", name="Bob").age == 0


def test_full_read_still_applies_defaults_and_required_checks():
    with MemoryBackend() as backend:
        # GIVEN stored items that lack fields
        backend.client.sync_put_item("users", {"pk": "USER#1", "name": "Ann"})
        backend.client.sync_put_item("users", {"pk": "USER#2"})

        # WHEN reading without a projection
        user = User.sync_batch_get([{"pk": "USER#1"}])[0]

        # THEN defaults apply and a missing required field fails
        assert user.age == 0
        with pytest.raises(ValueError, match="'name' is required"):
            User.sync_batch_get([{"pk": "USER#2"}])


class Ticket(Model):
    model_config = ModelConfig(table="tickets")
    pk = StringAttribute(partition_key=True)
    ref = StringAttribute(default=AutoGenerate.UUID4)
    title = StringAttribute()


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_does_not_auto_generate_fields_not_fetched(sync):
    with MemoryBackend() as backend:
        # GIVEN a ticket with a generated ref, loaded without it
        await Ticket(pk="T#1", title="Old").save()
        ref = backend.client.sync_get_item("tickets", {"pk": "T#1"})["ref"]
        ticket = await _load(Ticket, "batch_get", sync, ["pk", "title"], pk="T#1")

        # WHEN saving a change
        ticket.title = "New"
        await _save(ticket, sync)

        # THEN the stored ref is not replaced by a new one
        stored = backend.client.sync_get_item("tickets", {"pk": "T#1"})
        assert stored == {"pk": "T#1", "ref": ref, "title": "New"}


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True, template="ORDER#{order_id}")
    order_id = StringAttribute()
    status = StringAttribute()


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_keeps_template_key_when_placeholder_not_fetched(sync):
    with MemoryBackend() as backend:
        # GIVEN an order loaded without the key placeholder
        await Order(order_id="1", status="new").save()
        order = await _load(Order, "query", sync, ["pk", "status"], pk="ORDER#1")
        assert order.order_id is None

        # WHEN saving a change
        order.status = "paid"
        await _save(order, sync)

        # THEN the key is kept and only status changes
        assert backend.client.sync_get_item("orders", {"pk": "ORDER#1"}) == {
            "pk": "ORDER#1",
            "order_id": "1",
            "status": "paid",
        }


def test_template_key_is_built_from_fetched_placeholder():
    with MemoryBackend() as backend:
        # GIVEN an order loaded with the placeholder but without the key
        Order(order_id="1", status="new").sync_save()
        order = Order.sync_scan(fields=["order_id", "status"]).first()

        # WHEN saving a change
        assert order is not None
        assert order.pk == "ORDER#1"
        order.status = "paid"
        order.sync_save()

        # THEN the built key finds the stored item
        stored = backend.client.sync_get_item("orders", {"pk": "ORDER#1"})
        assert stored is not None
        assert stored["status"] == "paid"


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(partition_key=True)
    title = StringAttribute()
    version = VersionAttribute()


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_without_fetched_version_raises(sync):
    with MemoryBackend():
        # GIVEN a versioned document loaded without its version
        await Document(pk="D#1", title="Old").save()
        doc = await _load(Document, "batch_get", sync, ["pk", "title"], pk="D#1")
        doc.title = "New"

        # WHEN saving it
        # THEN it fails with a clear message
        with pytest.raises(ValueError, match="version attribute 'version' was not fetched"):
            await _save(doc, sync)


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_with_fetched_version_checks_and_bumps_it(sync):
    with MemoryBackend() as backend:
        # GIVEN a versioned document loaded with its version
        await Document(pk="D#1", title="Old").save()
        doc = await _load(Document, "batch_get", sync, ["pk", "title", "version"], pk="D#1")
        stale = await _load(Document, "batch_get", sync, ["pk", "version"], pk="D#1")

        # WHEN saving it without changes
        await _save(doc, sync)

        # THEN the version is bumped and a stale copy is rejected
        assert backend.client.sync_get_item("documents", {"pk": "D#1"}) == {
            "pk": "D#1",
            "title": "Old",
            "version": 2,
        }
        with pytest.raises(ConditionalCheckFailedException):
            await _save(stale, sync)


class Profile(Model):
    model_config = ModelConfig(table="profiles")
    pk = StringAttribute(partition_key=True)
    address = MapAttribute()


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_refuses_field_fetched_with_nested_path(sync):
    with MemoryBackend() as backend:
        # GIVEN a profile loaded with only part of its address
        stored = {"pk": "P#1", "address": {"city": "Lisbon", "street": "Main"}}
        await Profile(**stored).save()
        profile = await _load(Profile, "batch_get", sync, ["pk", "address.city"], pk="P#1")
        assert profile.address == {"city": "Lisbon"}

        # WHEN changing the address and saving
        profile.address = {"city": "Porto"}

        # THEN saving fails instead of replacing the whole address
        with pytest.raises(ValueError, match="Cannot save 'address'"):
            await _save(profile, sync)
        assert backend.client.sync_get_item("profiles", {"pk": "P#1"}) == stored


def test_save_after_update_tracks_saved_fields():
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection and saved with a change
        User(**STORED).sync_save()
        user = User.sync_batch_get([{"pk": "USER#1"}], projection=["pk", "name"])[0]
        user.email = "bob@example.com"
        user.sync_save()

        # WHEN saving again without changes
        user.sync_save()

        # THEN age is still kept, and email is now known
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == {
            **STORED,
            "email": "bob@example.com",
        }
        assert "email" not in user._not_fetched
        assert "age" in user._not_fetched


async def test_async_transaction_refuses_projected_model():
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        await User(**STORED).save()
        user = (await User.batch_get([{"pk": "USER#1"}], projection=["pk", "name"]))[0]

        # WHEN putting it in a transaction
        # THEN it fails, because a put would replace the full item
        with pytest.raises(ValueError, match="loaded with a projection"):
            async with Transaction(backend.client) as txn:
                txn.save_model(user)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED


def test_sync_transaction_refuses_projected_model():
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        User(**STORED).sync_save()
        user = User.sync_scan(fields=["pk", "name"]).first()

        # WHEN putting it in a transaction
        # THEN it fails, because a put would replace the full item
        with pytest.raises(ValueError, match="loaded with a projection"):
            with SyncTransaction(backend.client) as txn:
                txn.save_model(user)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED


class Account(Model):
    model_config = ModelConfig(table="accounts")
    pk = StringAttribute(partition_key=True)
    tags = ListAttribute()
    prefs = MapAttribute()
    labels = StringSetAttribute()
    details = MapAttribute()
    name = StringAttribute()


ACCOUNT = {
    "pk": "P#1",
    "tags": ["a"],
    "prefs": {"theme": "dark"},
    "labels": {"x"},
    "details": {"zip": "123"},
    "name": "Ann",
}


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_in_place_mutation_of_fetched_fields_is_saved(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a stored account loaded with a projection
        await Account(**ACCOUNT).save()
        account = await _load(Account, how, sync, ["pk", "tags", "prefs", "labels"], pk="P#1")

        # WHEN mutating the fetched collections in place
        account.tags.append("b")
        account.prefs["theme"] = "light"
        account.labels.add("y")
        await _save(account, sync)

        # THEN the changes are stored and the fields that were not fetched are kept
        stored = backend.client.sync_get_item("accounts", {"pk": "P#1"})
        assert stored["tags"] == ["a", "b"]
        assert stored["prefs"] == {"theme": "light"}
        assert set(stored["labels"]) == {"x", "y"}
        assert stored["details"] == {"zip": "123"}
        assert stored["name"] == "Ann"


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_in_place_mutation_is_saved_after_a_save(sync):
    with MemoryBackend() as backend:
        # GIVEN a projected account that was saved once
        await Account(**ACCOUNT).save()
        account = await _load(Account, "scan", sync, ["pk", "tags"], pk="P#1")
        account.tags.append("b")
        await _save(account, sync)

        # WHEN mutating it in place again
        account.tags.append("c")
        await _save(account, sync)

        # THEN the second change is stored too
        stored = backend.client.sync_get_item("accounts", {"pk": "P#1"})
        assert stored["tags"] == ["a", "b", "c"]
        assert stored["name"] == "Ann"


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_condition_is_checked_when_nothing_changed(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a stored user loaded with a projection and no changes
        await User(**STORED).save()
        user = await _load(User, how, sync, ["pk", "name"])

        # WHEN saving with a condition that is false
        # THEN it raises and the stored item is untouched
        with pytest.raises(ConditionalCheckFailedException):
            await _save(user, sync, condition=User.name == "Bob")
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED

        # AND a condition that is true saves without changing the item
        await _save(user, sync, condition=User.name == "Ann")
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == STORED


class Custom(Model):
    model_config = ModelConfig(table="customs")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute(required=True)
    age = NumberAttribute(default=0)

    loaded: list[dict[str, Any]] = []

    @classmethod
    def from_dict(cls, data):
        cls.loaded.append(dict(data))
        return super().from_dict(data)


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_projected_read_calls_custom_from_dict(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a model that overrides from_dict
        await Custom(pk="C#1", name="Ann", age=42).save()
        Custom.loaded.clear()

        # WHEN loading it with a projection
        custom = await _load(Custom, how, sync, ["pk", "name"], pk="C#1")

        # THEN the override ran and the model is still a projected one
        assert Custom.loaded == [{"pk": "C#1", "name": "Ann"}]
        assert custom.age is None
        custom.name = "Bob"
        await _save(custom, sync)
        assert backend.client.sync_get_item("customs", {"pk": "C#1"})["age"] == 42


def test_custom_from_dict_does_not_leak_projection_to_other_models():
    with MemoryBackend():
        # GIVEN a from_dict override that builds another model
        class Other(Model):
            model_config = ModelConfig(table="others")
            pk = StringAttribute(partition_key=True)
            name = StringAttribute(required=True)

        class Wrapper(Model):
            model_config = ModelConfig(table="wrappers")
            pk = StringAttribute(partition_key=True)

            @classmethod
            def from_dict(cls, data):
                with pytest.raises(ValueError, match="required"):
                    Other.from_dict({"pk": "O#1"})
                return super().from_dict(data)

        Wrapper(pk="W#1").sync_save()

        # WHEN loading the wrapper with a projection
        wrapper = Wrapper.sync_scan(fields=["pk"]).first()

        # THEN the other model still validates required fields
        assert wrapper is not None


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_save_refuses_nested_field_missing_from_the_item(how, sync):
    with MemoryBackend() as backend:
        # GIVEN details holds zip, and the projection asks for a missing nested path
        await Account(**ACCOUNT).save()
        account = await _load(Account, how, sync, ["pk", "details.city"], pk="P#1")
        assert account.details is None

        # WHEN replacing details and saving
        account.details = {"city": "new"}

        # THEN it raises instead of deleting zip
        with pytest.raises(ValueError, match="nested projection"):
            await _save(account, sync)
        stored = backend.client.sync_get_item("accounts", {"pk": "P#1"})
        assert stored["details"] == {"zip": "123"}


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_second_save_keeps_attributes_outside_the_schema(how, sync):
    with MemoryBackend() as backend:
        # GIVEN a stored user with an attribute the model does not declare
        stored = {**STORED, "legacy": "keep"}
        backend.client.sync_put_item("users", stored)
        user = await _load(User, how, sync, ["pk", "name"])

        # WHEN saving every field that was not fetched, then saving again
        user.age = 43
        user.email = "new@example.com"
        await _save(user, sync)
        await _save(user, sync)

        # THEN the attribute outside the schema is still stored
        item = backend.client.sync_get_item("users", {"pk": "USER#1"})
        assert item["legacy"] == "keep"
        assert item["age"] == 43
