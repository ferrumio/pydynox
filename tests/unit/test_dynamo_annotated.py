"""Tests for ``Annotated[..., Dynamo.*]`` model field declarations."""

from __future__ import annotations

import warnings
from typing import Annotated, ClassVar
from unittest.mock import MagicMock

import pytest
from pydynox import Dynamo, DynamoConfig, Model
from pydynox.attributes import StringAttribute


def test_annotated_declarations_match_descriptors() -> None:
    """Synthesized attributes are equivalent to class-body StringAttribute declarations."""

    class UserAnnotated(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="t")
        pk: Annotated[str, Dynamo.String(partition_key=True)]
        name: Annotated[str, Dynamo.String()]

    class UserLegacy(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="t")
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    for attr_name in ("pk", "name"):
        a = UserAnnotated._attributes[attr_name]
        b = UserLegacy._attributes[attr_name]
        assert type(a) is type(b)
        assert a.partition_key == b.partition_key
        assert a.sort_key == b.sort_key
        assert a.required == b.required
        assert a.default == b.default
        assert a.alias == b.alias
        assert a.discriminator == b.discriminator

    assert UserAnnotated._partition_key == "pk"
    assert UserLegacy._partition_key == "pk"
    item = {"pk": "P1", "name": "Ann"}
    assert UserAnnotated.from_dict(item).to_dict() == item
    assert UserLegacy.from_dict(item).to_dict() == item


def test_descriptor_in_namespace_wins() -> None:
    """If the class body assigns an ``Attribute`` after an annotation, it wins."""

    class User(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="t")
        pk: Annotated[str, Dynamo.String(partition_key=True)]
        # Override synthesizer with a concrete descriptor
        name: Annotated[str, Dynamo.String()]
        name = StringAttribute(alias="n")

    assert User._attributes["name"].alias == "n"


def test_fails_on_second_partition_key() -> None:
    """Defining a second partition key (including via Annotated) is rejected."""

    with pytest.raises(ValueError, match="more than one partition key"):

        class _Bad(Model):  # noqa: D401
            dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="t")
            a: Annotated[str, Dynamo.String(partition_key=True)]
            b: Annotated[str, Dynamo.String(partition_key=True)]


@pytest.mark.asyncio
async def test_annotated_model_crud_roundtrip() -> None:
    """Minimal async get with Annotated model (same pattern as other unit tests)."""
    mock_client = MagicMock()

    async def mock_get_item(table, key, consistent_read=False):
        return {"pk": "1", "age": 30}

    mock_client.get_item = mock_get_item

    class Record(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(
            table="recs", client=mock_client
        )
        pk: Annotated[str, Dynamo.String(partition_key=True)]
        age: Annotated[int, Dynamo.Number()]

    Record._client_instance = None
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        r = await Record.get(pk="1")
    assert r is not None
    assert r.pk == "1"
    assert r.age == 30
