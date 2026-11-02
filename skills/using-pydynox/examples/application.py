"""Public API examples: memory by default, LocalStack with --endpoint-url."""

from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from pydynox import (
    BatchWriter,
    DynamoDBClient,
    Model,
    ModelConfig,
    SyncBatchWriter,
    SyncTransaction,
    Transaction,
    get_default_client,
    set_default_client,
)
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend


class Order(Model):
    model_config = ModelConfig(table="skill_orders", consistent_read=True)
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total_cents = NumberAttribute(default=0)
    status = StringAttribute(default="pending")


async def crud(customer_id: str) -> None:
    order = Order(pk=f"CUSTOMER#{customer_id}", sk="ORDER#001", total_cents=1200)
    await order.save(condition=Order.pk.not_exists())
    found = await Order.get(pk=order.pk, sk=order.sk)
    assert found is not None and found.total_cents == 1200
    await found.update(status="paid", condition=(Order.status == "pending"))
    paid = await Order.get(pk=order.pk, sk=order.sk)
    assert paid is not None and paid.status == "paid"
    await paid.delete()
    assert await Order.get(pk=order.pk, sk=order.sk) is None


def sync_crud(customer_id: str) -> None:
    order = Order(pk=f"CUSTOMER#{customer_id}", sk="ORDER#001", total_cents=1200)
    order.sync_save(condition=Order.pk.not_exists())
    found = Order.sync_get(pk=order.pk, sk=order.sk)
    assert found is not None and found.total_cents == 1200
    found.sync_update(status="paid", condition=(Order.status == "pending"))
    paid = Order.sync_get(pk=order.pk, sk=order.sk)
    assert paid is not None and paid.status == "paid"
    paid.sync_delete()
    assert Order.sync_get(pk=order.pk, sk=order.sk) is None


def order_items(customer_id: str) -> list[dict[str, str | int]]:
    return [
        {
            "pk": f"CUSTOMER#{customer_id}",
            "sk": f"ORDER#{index:03d}",
            "total_cents": 100 * index,
            "status": "pending",
        }
        for index in range(3)
    ]


async def query_and_batch(customer_id: str) -> None:
    client = get_default_client()
    assert client is not None
    items = order_items(customer_id)
    async with BatchWriter(client, Order.model_config.table) as batch:
        for item in items:
            batch.put(item)
    orders = [order async for order in Order.query(partition_key=items[0]["pk"])]
    assert {order.sk for order in orders} == {item["sk"] for item in items}
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    loaded = await Order.batch_get(keys, consistent_read=True)
    assert {order.sk for order in loaded} == {item["sk"] for item in items}


async def pagination(customer_id: str) -> None:
    await query_and_batch(customer_id)
    items = order_items(customer_id)
    result = Order.query(partition_key=items[0]["pk"], limit=2, page_size=1)
    first = [order async for order in result]
    assert [order.sk for order in first] == ["ORDER#000", "ORDER#001"]
    assert result.last_evaluated_key is not None
    rest = [
        order
        async for order in Order.query(
            partition_key=items[0]["pk"], last_evaluated_key=result.last_evaluated_key
        )
    ]
    assert [order.sk for order in rest] == ["ORDER#002"]


def sync_query_and_batch(customer_id: str) -> None:
    client = get_default_client()
    assert client is not None
    items = order_items(customer_id)
    with SyncBatchWriter(client, Order.model_config.table) as batch:
        for item in items:
            batch.put(item)
    orders = list(Order.sync_query(partition_key=items[0]["pk"]))
    assert {order.sk for order in orders} == {item["sk"] for item in items}
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    loaded = Order.sync_batch_get(keys, consistent_read=True)
    assert {order.sk for order in loaded} == {item["sk"] for item in items}


def sync_pagination(customer_id: str) -> None:
    sync_query_and_batch(customer_id)
    items = order_items(customer_id)
    result = Order.sync_query(partition_key=items[0]["pk"], limit=2, page_size=1)
    first = list(result)
    assert [order.sk for order in first] == ["ORDER#000", "ORDER#001"]
    assert result.last_evaluated_key is not None
    rest = list(
        Order.sync_query(partition_key=items[0]["pk"], last_evaluated_key=result.last_evaluated_key)
    )
    assert [order.sk for order in rest] == ["ORDER#002"]


async def transaction(customer_id: str) -> None:
    client = get_default_client()
    assert client is not None
    items = order_items(customer_id)
    async with Transaction(client) as tx:
        for item in items:
            tx.put(Order.model_config.table, item)
    orders = [order async for order in Order.query(partition_key=items[0]["pk"])]
    assert {order.sk for order in orders} == {item["sk"] for item in items}


def sync_transaction(customer_id: str) -> None:
    client = get_default_client()
    assert client is not None
    items = order_items(customer_id)
    with SyncTransaction(client) as tx:
        for item in items:
            tx.put(Order.model_config.table, item)
    orders = list(Order.sync_query(partition_key=items[0]["pk"]))
    assert {order.sk for order in orders} == {item["sk"] for item in items}


async def async_examples(localstack: bool) -> None:
    await crud(uuid4().hex)
    await query_and_batch(uuid4().hex)
    if localstack:
        await pagination(uuid4().hex)
        await transaction(uuid4().hex)


def run_examples(localstack: bool) -> None:
    asyncio.run(async_examples(localstack))
    sync_crud(uuid4().hex)
    sync_query_and_batch(uuid4().hex)
    if localstack:
        sync_pagination(uuid4().hex)
        sync_transaction(uuid4().hex)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-url", help="LocalStack endpoint; omit for in-memory examples")
    args = parser.parse_args()
    if args.endpoint_url:
        client = DynamoDBClient(
            region="us-east-1",
            endpoint_url=args.endpoint_url,
            access_key="testing",
            secret_key="testing",
        )
        set_default_client(client)
        if not Order.sync_table_exists():
            Order.sync_create_table(wait=True)
        run_examples(localstack=True)
    else:
        with MemoryBackend():
            run_examples(localstack=False)
    print("All examples passed.")


if __name__ == "__main__":
    main()
