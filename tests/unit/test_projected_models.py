"""Unit tests for models loaded with a projection (batch_get, query, scan)."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import AutoGenerate, Model, ModelConfig, SyncTransaction, Transaction
from pydynox._internal._s3 import S3File, S3Value
from pydynox.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    S3Attribute,
    StringAttribute,
    StringSetAttribute,
    VersionAttribute,
)
from pydynox.exceptions import ConditionalCheckFailedException
from pydynox.hooks import before_save
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


async def _load(
    model: Any,
    how: str,
    sync: bool,
    fields: list[str],
    pk: str = "USER#1",
    sk: str | None = None,
) -> Any:
    """Load one model through batch_get, query, or scan with a projection."""
    if how == "batch_get":
        key = {"pk": pk}
        if sk is not None:
            key["sk"] = sk
        if sync:
            return model.sync_batch_get([key], projection=fields)[0]
        return (await model.batch_get([key], projection=fields))[0]
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


@pytest.fixture
def s3_storage():
    objects = {}

    def upload(bucket, key, data, content_type, metadata):
        objects[bucket, key] = data
        result = SimpleNamespace(
            bucket=bucket,
            key=key,
            size=len(data),
            etag=data.hex(),
            content_type=content_type,
            last_modified=None,
            version_id=None,
            metadata=metadata,
        )
        metrics = SimpleNamespace(
            duration_ms=1.0, calls=1, bytes_uploaded=len(data), bytes_downloaded=0
        )
        return result, metrics

    ops = MagicMock()
    ops.sync_upload_bytes.side_effect = upload
    ops.upload_bytes = AsyncMock(side_effect=upload)
    return objects, ops


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize(
    ("rejection", "error"),
    [
        ("template", "Cannot save 'gsi_pk'"),
        ("missing_placeholder", "Cannot save 'gsi_pk'"),
        ("partial_template", "Cannot save 'gsi_pk'"),
        ("missing_key", "key attribute 'pk' was not fetched"),
        ("missing_version", "version attribute 'version' was not fetched"),
        ("nested", "Cannot save 'address'"),
        ("hook", "Cannot save 'gsi_pk'"),
    ],
)
async def test_projected_rejection_precedes_s3_upload(how, sync, rejection, error, s3_storage):
    objects, ops = s3_storage
    hook_calls = []

    class Attachment(Model):
        model_config = ModelConfig(table="attachments")
        pk = StringAttribute(partition_key=True)
        status = StringAttribute()
        tenant = StringAttribute()
        address = MapAttribute()
        gsi_pk = StringAttribute(
            template=(
                "ADDR#{address}"
                if rejection == "partial_template"
                else "STATE#{tenant}#{status}"
                if rejection == "missing_placeholder"
                else "STATE#{status}"
            )
        )
        content = S3Attribute(bucket="files", prefix="docs/")
        version = VersionAttribute()

        @before_save
        def change_status(self):
            hook_calls.append("before_save")
            if getattr(self, "_change_status", False):
                self.status = "paid"

    Attachment._attributes["content"]._s3_ops = ops
    with MemoryBackend() as backend:
        attachment = Attachment(
            pk="D#1",
            status="new",
            tenant="T#1",
            address={"city": "Lisbon", "street": "Main"},
            content=S3File(b"original", name="report.pdf"),
        )
        await _save(attachment, sync)
        stored = backend.client.sync_get_item("attachments", {"pk": "D#1"})
        original_objects = dict(objects)
        ops.reset_mock()
        hook_calls.clear()
        fields = ["pk", "status", "version"]
        if rejection == "missing_key":
            fields.remove("pk")
        elif rejection == "missing_version":
            fields.remove("version")
        elif rejection in ("partial_template", "nested"):
            fields.append("address.city")
        if rejection in ("partial_template", "missing_placeholder"):
            fields.append("gsi_pk")
        attachment = await _load(Attachment, how, sync, fields, pk="D#1")
        if rejection in ("template", "missing_placeholder"):
            attachment.status = "paid"
        elif rejection in ("partial_template", "nested"):
            attachment.address["city"] = "Porto"
        elif rejection == "hook":
            attachment._change_status = True
        replacement = S3File(b"replacement", name="report.pdf")
        attachment.content = replacement
        version = attachment.version

        with pytest.raises(ValueError, match=error):
            await _save(attachment, sync)

        assert objects == original_objects
        ops.sync_upload_bytes.assert_not_called()
        ops.upload_bytes.assert_not_awaited()
        assert attachment.content is replacement
        assert attachment.version == version
        assert hook_calls == ["before_save"]
        assert backend.client.sync_get_item("attachments", {"pk": "D#1"}) == stored


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_s3_save_prepares_hooks_keys_and_uploaded_metadata(sync, s3_storage):
    objects, ops = s3_storage
    hook_calls = []

    class GeneratedAttachment(Model):
        model_config = ModelConfig(table="generated_attachments")
        pk = StringAttribute(partition_key=True, template="DOC#{doc_id}")
        doc_id = StringAttribute(default=AutoGenerate.UUID4)
        content = S3Attribute(bucket="files", prefix="docs/")
        label = StringAttribute(template="FILE#{content}")
        note = StringAttribute(default="keep")
        version = VersionAttribute()

        @before_save
        def supply_file(self):
            hook_calls.append("before_save")
            if self.content is None:
                self.content = S3File(b"original", name="report.pdf")

    GeneratedAttachment._attributes["content"]._s3_ops = ops
    with MemoryBackend() as backend:
        attachment = GeneratedAttachment()
        await _save(attachment, sync)
        assert isinstance(attachment.content, S3Value)
        assert attachment.content.key == f"docs/DOC/{attachment.doc_id}/report.pdf"
        assert objects["files", attachment.content.key] == b"original"
        assert attachment.label == f"FILE#{attachment.content}"
        assert hook_calls == ["before_save"]
        hook_calls.clear()
        GeneratedAttachment.reset_metrics()
        pk = attachment.pk
        attachment = await _load(
            GeneratedAttachment, "batch_get", sync, ["pk", "doc_id", "label", "version"], pk=pk
        )
        attachment.content = S3File(b"replacement", name="report.pdf")
        await _save(attachment, sync)

        assert isinstance(attachment.content, S3Value)
        assert objects["files", attachment.content.key] == b"replacement"
        assert attachment.label == f"FILE#{attachment.content}"
        assert hook_calls == ["before_save"]
        stored = backend.client.sync_get_item("generated_attachments", {"pk": pk})
        assert stored["content"]["etag"] == b"replacement".hex()
        assert stored["label"] == attachment.label
        assert stored["note"] == "keep"
        assert stored["version"] == 2
        metrics = GeneratedAttachment.get_total_metrics()
        assert metrics.s3_calls == 1
        assert metrics.s3_bytes_uploaded == len(b"replacement")


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
@pytest.mark.parametrize(
    "fields, expected",
    [
        (["pk", "name"], {"pk": "USER#1", "name": "Ann"}),
        (["pk", "name", "age", "email"], STORED),
    ],
)
async def test_full_replace_writes_only_fetched_fields(sync, fields, expected):
    with MemoryBackend() as backend:
        # GIVEN a user loaded with a projection
        backend.client.sync_put_item("users", {**STORED, "legacy": "keep"})
        user = await _load(User, "batch_get", sync, fields)

        # WHEN asking for a full replace
        await _save(user, sync, full_replace=True)

        # THEN the item is replaced with the fetched fields only
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == expected


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


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_full_schema_projection_keeps_attributes_outside_the_schema(how, sync):
    with MemoryBackend() as backend:
        stored = {**STORED, "legacy": "keep"}
        backend.client.sync_put_item("users", stored)
        user = await _load(User, how, sync, ["pk", "name", "age", "email"])
        assert user.age == 42

        await _save(user, sync)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == stored

        user.name = "Bob"
        await _save(user, sync)
        await _save(user, sync)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == {
            **stored,
            "name": "Bob",
        }


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


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize("missing_placeholder", [False, True])
async def test_save_rejects_changes_to_skipped_template_dependencies(how, sync, missing_placeholder):
    class IndexedOrder(Model):
        model_config = ModelConfig(table="indexed_orders")
        pk = StringAttribute(partition_key=True)
        status = StringAttribute()
        tenant = StringAttribute()
        gsi_pk = StringAttribute(
            template="STATE#{tenant}#{status}" if missing_placeholder else "STATE#{status}",
            alias="state_key",
        )
        note = StringAttribute()
        version = VersionAttribute()

    with MemoryBackend() as backend:
        await IndexedOrder(pk="O#1", status="new", tenant="T#1", note="old").save()
        stored = backend.client.sync_get_item("indexed_orders", {"pk": "O#1"})
        fields = ["pk", "status", "note", "version"]
        if missing_placeholder:
            fields.append("gsi_pk")
        order = await _load(IndexedOrder, how, sync, fields, pk="O#1")
        expected_key = stored["state_key"] if missing_placeholder else None
        assert order.gsi_pk == expected_key

        order.status = "paid"
        with pytest.raises(ValueError, match="Cannot save 'gsi_pk'.*'status'"):
            await _save(order, sync)
        assert order.version == 1
        assert order.gsi_pk == expected_key
        assert backend.client.sync_get_item("indexed_orders", {"pk": "O#1"}) == stored

        order.status = "new"
        order.note = "updated"
        await _save(order, sync)
        assert order.gsi_pk == expected_key
        assert backend.client.sync_get_item("indexed_orders", {"pk": "O#1"}) == {
            **stored,
            "note": "updated",
            "version": 2,
        }

        order = await _load(
            IndexedOrder, how, sync, ["pk", "status", "tenant", "gsi_pk", "version"], pk="O#1"
        )
        order.status = "paid"
        await _save(order, sync)
        expected_key = "STATE#T#1#paid" if missing_placeholder else "STATE#paid"
        assert backend.client.sync_get_item("indexed_orders", {"pk": "O#1"}) == {
            **stored,
            "status": "paid",
            "state_key": expected_key,
            "note": "updated",
            "version": 3,
        }


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
async def test_save_rejects_mutated_skipped_template_dependency(sync):
    class TaggedOrder(Model):
        model_config = ModelConfig(table="tagged_orders")
        pk = StringAttribute(partition_key=True)
        tags = ListAttribute()
        label = StringAttribute(template="TAGS#{tags}")

    with MemoryBackend() as backend:
        await TaggedOrder(pk="O#1", tags=["new"]).save()
        stored = backend.client.sync_get_item("tagged_orders", {"pk": "O#1"})
        order = await _load(TaggedOrder, "scan", sync, ["pk", "tags"], pk="O#1")
        order.tags.append("paid")
        with pytest.raises(ValueError, match="Cannot save 'label'.*'tags'"):
            await _save(order, sync)
        assert order.label is None
        assert backend.client.sync_get_item("tagged_orders", {"pk": "O#1"}) == stored


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize("fetch_template", [False, True])
@pytest.mark.parametrize(
    ("status_path", "change"),
    [
        ("status.code", "assign"),
        ("status.code", "in_place"),
        ("status.code", "sibling"),
        ("status.missing", "assign"),
        ("status.missing", "sibling"),
    ],
)
async def test_save_keeps_template_with_partially_fetched_dependency(
    how, sync, fetch_template, status_path, change
):
    class IndexedProfile(Model):
        model_config = ModelConfig(table="indexed_profiles")
        pk = StringAttribute(partition_key=True)
        status = MapAttribute()
        tenant = StringAttribute()
        gsi_pk = StringAttribute(template="STATE#{status}#{tenant}", alias="state_key")
        note = StringAttribute()
        version = VersionAttribute()

    with MemoryBackend() as backend:
        await IndexedProfile(
            pk="P#1", status={"code": "new", "region": "eu"}, tenant="T#1", note="old"
        ).save()
        stored = backend.client.sync_get_item("indexed_profiles", {"pk": "P#1"})
        fields = ["pk", status_path, "tenant", "note", "version"]
        if fetch_template:
            fields.append("gsi_pk")
        profile = await _load(IndexedProfile, how, sync, fields, pk="P#1")
        expected_key = stored["state_key"] if fetch_template else None
        assert profile.status == ({"code": "new"} if status_path == "status.code" else None)

        await _save(profile, sync)
        assert profile.gsi_pk == expected_key
        assert backend.client.sync_get_item("indexed_profiles", {"pk": "P#1"}) == {
            **stored,
            "version": 2,
        }

        profile.note = "updated"
        await _save(profile, sync)
        assert profile.gsi_pk == expected_key
        saved = {**stored, "note": "updated", "version": 3}
        assert backend.client.sync_get_item("indexed_profiles", {"pk": "P#1"}) == saved

        if change == "in_place":
            profile.status["code"] = "paid"
        elif change == "sibling":
            profile.tenant = "T#2"
        else:
            profile.status = {"code": "paid"}
        dependency = "tenant" if change == "sibling" else "status"
        with pytest.raises(ValueError, match=f"Cannot save 'gsi_pk'.*'{dependency}'"):
            await _save(profile, sync)
        assert profile.gsi_pk == expected_key
        assert profile.version == 3
        assert backend.client.sync_get_item("indexed_profiles", {"pk": "P#1"}) == saved

        profile = await _load(
            IndexedProfile, how, sync, ["pk", "status", "tenant", "gsi_pk", "version"], pk="P#1"
        )
        profile.status["code"] = "paid"
        await _save(profile, sync)
        full_status = {**stored["status"], "code": "paid"}
        assert backend.client.sync_get_item("indexed_profiles", {"pk": "P#1"}) == {
            **saved,
            "status": full_status,
            "state_key": f"STATE#{full_status}#T#1",
            "version": 4,
        }


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
async def test_unfetched_template_key_stays_none(how, sync):
    with MemoryBackend() as backend:
        Order(order_id="1", status="new").sync_save()
        order = await _load(Order, how, sync, ["order_id", "status"], pk="ORDER#1")
        assert order.pk is None

        order.status = "paid"
        with pytest.raises(ValueError, match="key attribute 'pk' was not fetched"):
            await _save(order, sync)
        assert order.pk is None
        assert backend.client.sync_get_item("orders", {"pk": "ORDER#1"}) == {
            "pk": "ORDER#1",
            "order_id": "1",
            "status": "new",
        }


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize("omitted", ["pk", "sk", "label"])
async def test_unfetched_aliased_templates_stay_none(how, sync, omitted):
    class Shipment(Model):
        model_config = ModelConfig(table="shipments")
        pk = StringAttribute(partition_key=True, template="ORDER#{order_id}", alias="partition")
        sk = StringAttribute(sort_key=True, template="PROFILE", alias="sort")
        label = StringAttribute(template="LABEL#{order_id}", alias="display")
        order_id = StringAttribute()
        status = StringAttribute()

    with MemoryBackend() as backend:
        Shipment(order_id="1", status="new").sync_save()
        key = {"partition": "ORDER#1", "sort": "PROFILE"}
        stored = backend.client.sync_get_item("shipments", key)
        fields = [
            name for name in ("pk", "sk", "label", "order_id", "status") if name != omitted
        ]
        shipment = await _load(Shipment, how, sync, fields, pk="ORDER#1", sk="PROFILE")
        assert getattr(shipment, omitted) is None

        shipment.status = "paid"
        if omitted in ("pk", "sk"):
            with pytest.raises(ValueError, match=f"key attribute '{omitted}' was not fetched"):
                await _save(shipment, sync)
            assert backend.client.sync_get_item("shipments", key) == stored
        else:
            await _save(shipment, sync)
            await _save(shipment, sync)
            assert backend.client.sync_get_item("shipments", key) == {**stored, "status": "paid"}
        assert getattr(shipment, omitted) is None


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


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize("in_place", [False, True])
async def test_nested_projection_rejection_preserves_version_for_retry(how, sync, in_place):
    class VersionedProfile(Model):
        model_config = ModelConfig(table="versioned_profiles")
        pk = StringAttribute(partition_key=True)
        title = StringAttribute()
        address = MapAttribute()
        version = VersionAttribute()

    with MemoryBackend() as backend:
        await VersionedProfile(
            pk="P#1", title="old", address={"city": "Lisbon", "street": "Main"}
        ).save()
        stored = backend.client.sync_get_item("versioned_profiles", {"pk": "P#1"})
        profile = await _load(
            VersionedProfile, how, sync, ["pk", "title", "address.city", "version"], pk="P#1"
        )
        if in_place:
            profile.address["city"] = "Porto"
        else:
            profile.address = {"city": "Porto"}
        with pytest.raises(ValueError, match="Cannot save 'address'"):
            await _save(profile, sync)
        assert profile.version == 1
        assert backend.client.sync_get_item("versioned_profiles", {"pk": "P#1"}) == stored

        profile.address = {"city": "Lisbon"}
        profile.title = "new"
        await _save(profile, sync)
        assert profile.version == 2
        assert backend.client.sync_get_item("versioned_profiles", {"pk": "P#1"}) == {
            **stored,
            "title": "new",
            "version": 2,
        }


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


@pytest.mark.parametrize("sync", MODES, ids=["async", "sync"])
@pytest.mark.parametrize("how", LOADERS)
@pytest.mark.parametrize("fields", [["pk", "name"], ["pk", "name", "age", "email"]])
async def test_transaction_refuses_projected_model(how, sync, fields):
    with MemoryBackend() as backend:
        stored = {**STORED, "legacy": "keep"}
        backend.client.sync_put_item("users", stored)
        user = await _load(User, how, sync, fields)

        with pytest.raises(ValueError, match="loaded with a projection"):
            if sync:
                with SyncTransaction(backend.client) as txn:
                    txn.save_model(user)
            else:
                async with Transaction(backend.client) as txn:
                    txn.save_model(user)
        assert backend.client.sync_get_item("users", {"pk": "USER#1"}) == stored


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
