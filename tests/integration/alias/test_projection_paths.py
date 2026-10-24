"""Projections preserve literal dots in attribute aliases."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import MapAttribute, StringAttribute


@pytest.mark.asyncio
@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
@pytest.mark.parametrize("operation", ["batch_get", "query", "scan"])
@pytest.mark.parametrize("field", ["address", "address.city"])
@pytest.mark.parametrize("as_dict", [False, True], ids=["model", "dict"])
async def test_projection_preserves_dots_in_alias(dynamo, sync, operation, field, as_dict):
    # GIVEN a literal dotted attribute and a different nested path with the same spelling
    class Customer(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        address = MapAttribute(alias="contact.addr")

    key = {"pk": f"DOT#{uuid.uuid4()}", "sk": "PROFILE"}
    address = {"city": "Paris", "zip": "75001"}
    await dynamo.put_item(
        "test_table",
        {
            **key,
            "contact.addr": address,
            "contact": {"addr": {"city": "Wrong path", "zip": "00000"}},
        },
    )

    # WHEN projecting the whole aliased attribute or one of its nested fields
    fields = ["pk", "sk", field]
    if operation == "batch_get":
        if sync:
            results = Customer.sync_batch_get([key], projection=fields, as_dict=as_dict)
        else:
            results = await Customer.batch_get([key], projection=fields, as_dict=as_dict)
    elif operation == "query":
        if sync:
            results = list(
                Customer.sync_query(partition_key=key["pk"], fields=fields, as_dict=as_dict)
            )
        else:
            results = [
                item
                async for item in Customer.query(
                    partition_key=key["pk"], fields=fields, as_dict=as_dict
                )
            ]
    else:
        if sync:
            results = list(
                Customer.sync_scan(
                    filter_condition=Customer.pk == key["pk"], fields=fields, as_dict=as_dict
                )
            )
        else:
            results = [
                item
                async for item in Customer.scan(
                    filter_condition=Customer.pk == key["pk"], fields=fields, as_dict=as_dict
                )
            ]

    # THEN the literal alias is returned, without reading the similarly named nested path
    expected = address if field == "address" else {"city": "Paris"}
    assert len(results) == 1
    if as_dict:
        assert results[0] == {**key, "contact.addr": expected}
    else:
        assert results[0].address == expected
