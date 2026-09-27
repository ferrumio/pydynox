"""Verify transaction idempotency against DynamoDB through LocalStack."""

from uuid import uuid4

import pytest
from pydynox import SyncTransaction, Transaction
from pydynox.exceptions import IdempotentParameterMismatchException, PydynoxException


@pytest.fixture
def stock_item(dynamo):
    key = {"pk": f"IDEMPOTENCY#{uuid4()}", "sk": "STOCK"}
    dynamo.sync_put_item("test_table", {**key, "stock": 10})
    return key


@pytest.fixture(params=["async_client", "sync_client", "async_context", "sync_context"])
def reserve_stock(request, dynamo, stock_item):
    """Exercise the same stock reservation through all four public entry points."""

    async def reserve(quantity=1, **kwargs):
        update = {
            "table": "test_table",
            "key": stock_item,
            "update_expression": "SET #stock = #stock - :quantity",
            "condition_expression": "#stock >= :quantity",
            "expression_attribute_names": {"#stock": "stock"},
            "expression_attribute_values": {":quantity": quantity},
        }
        if request.param == "async_context":
            async with Transaction(dynamo, **kwargs) as tx:
                tx.update(**update)
        elif request.param == "sync_context":
            with SyncTransaction(dynamo, **kwargs) as tx:
                tx.update(**update)
        elif request.param == "async_client":
            await dynamo.transact_write([{"type": "update", **update}], **kwargs)
        else:
            dynamo.sync_transact_write([{"type": "update", **update}], **kwargs)

    return reserve


async def test_identical_token_does_not_reserve_twice(dynamo, stock_item, reserve_stock):
    # GIVEN a stable token for one logical reservation
    token = str(uuid4())

    # WHEN the same request is submitted twice through separate calls
    await reserve_stock(client_request_token=token)
    await reserve_stock(client_request_token=token)

    # THEN stock is decremented only once
    item = dynamo.sync_get_item("test_table", stock_item, consistent_read=True)
    assert item["stock"] == 9

    # WHEN a new reservation uses a different token, THEN it applies independently
    await reserve_stock(client_request_token=str(uuid4()))
    item = dynamo.sync_get_item("test_table", stock_item, consistent_read=True)
    assert item["stock"] == 8


async def test_token_reuse_with_different_operations_raises(dynamo, stock_item, reserve_stock):
    # GIVEN a completed reservation
    token = str(uuid4())
    await reserve_stock(client_request_token=token)

    # WHEN the token is reused for a different quantity, THEN a specific error is raised
    with pytest.raises(IdempotentParameterMismatchException) as error:
        await reserve_stock(quantity=2, client_request_token=token)

    assert isinstance(error.value, PydynoxException)
    item = dynamo.sync_get_item("test_table", stock_item, consistent_read=True)
    assert item["stock"] == 9


@pytest.mark.parametrize("kwargs", [{}, {"client_request_token": None}], ids=["omitted", "none"])
async def test_without_explicit_token_each_call_applies(dynamo, stock_item, reserve_stock, kwargs):
    # GIVEN no caller-provided token
    # WHEN the operation is submitted twice
    await reserve_stock(**kwargs)
    await reserve_stock(**kwargs)

    # THEN the SDK generates independent tokens, preserving the existing behavior
    item = dynamo.sync_get_item("test_table", stock_item, consistent_read=True)
    assert item["stock"] == 8
