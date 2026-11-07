"""Query recipes for LocalStack; filtered pages need the fix after pydynox 1.8.0."""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import Any
from uuid import uuid4

from pydynox import (
    DynamoDBClient,
    Model,
    ModelConfig,
    SyncBatchWriter,
    get_default_client,
    set_default_client,
)
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class Order(Model):
    model_config = ModelConfig(table="skill_query_orders", consistent_read=True)
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    status = StringAttribute()
    customer_status = StringAttribute()
    total_cents = NumberAttribute()

    customer_status_index = GlobalSecondaryIndex(
        index_name="customer-status-index",
        partition_key="customer_status",
        sort_key="sk",
        projection="ALL",
    )


def seed(customer_id: str) -> str:
    """Local test setup. The first three orders do not match the paid filter."""
    client = get_default_client()
    assert client is not None
    pk = f"CUSTOMER#{customer_id}"
    with SyncBatchWriter(client, Order.model_config.table) as batch:
        for index in range(7):
            status = "pending" if index < 3 else "paid"
            batch.put(
                Order(
                    pk=pk,
                    sk=f"ORDER#{index:03d}",
                    status=status,
                    customer_status=f"{pk}#{status}",
                    total_cents=100 * index,
                ).to_dict()
            )
    return pk


async def order_page(
    customer_pk: str,
    cursor: dict[str, Any] | None = None,
    *,
    page_limit: int = 3,
    status: str | None = None,
    descending: bool = False,
) -> tuple[list[Order], dict[str, Any] | None]:
    """Return a bounded page and a cursor without skipping buffered results."""
    if page_limit < 1:
        raise ValueError("page_limit must be positive")
    result = Order.query(
        partition_key=customer_pk,
        sort_key_condition=Order.sk.begins_with("ORDER#"),
        filter_condition=(Order.status == status) if status is not None else None,
        limit=page_limit,
        # One evaluated item per request keeps the cursor at a delivery boundary.
        # See references/pagination.md for the throughput tradeoff.
        page_size=1,
        scan_index_forward=not descending,
        last_evaluated_key=cursor,
    )
    items = [order async for order in result]
    return items, result.last_evaluated_key


def sync_order_page(
    customer_pk: str,
    cursor: dict[str, Any] | None = None,
    *,
    page_limit: int = 3,
    status: str | None = None,
    descending: bool = False,
) -> tuple[list[Order], dict[str, Any] | None]:
    """Sync equivalent of order_page, with the same cursor contract."""
    if page_limit < 1:
        raise ValueError("page_limit must be positive")
    result = Order.sync_query(
        partition_key=customer_pk,
        sort_key_condition=Order.sk.begins_with("ORDER#"),
        filter_condition=(Order.status == status) if status is not None else None,
        limit=page_limit,
        page_size=1,
        scan_index_forward=not descending,
        last_evaluated_key=cursor,
    )
    items = list(result)
    return items, result.last_evaluated_key


async def pagination(customer_id: str) -> None:
    pk = seed(customer_id)
    cursor = None
    keys = []
    for _ in range(10):
        items, cursor = await order_page(pk, cursor)
        keys.extend(order.sk for order in items)
        if cursor is None:
            break
    else:
        raise AssertionError("Pagination did not exhaust")
    assert keys == [f"ORDER#{i:03d}" for i in range(7)]
    assert await order_page(f"{pk}#missing") == ([], None)


def sync_pagination(customer_id: str) -> None:
    pk = seed(customer_id)
    cursor = None
    keys = []
    for _ in range(10):
        items, cursor = sync_order_page(pk, cursor, descending=True)
        keys.extend(order.sk for order in items)
        if cursor is None:
            break
    else:
        raise AssertionError("Pagination did not exhaust")
    assert keys == [f"ORDER#{i:03d}" for i in reversed(range(7))]
    assert sync_order_page(f"{pk}#missing") == ([], None)


async def filtered_pages(customer_id: str) -> None:
    pk = seed(customer_id)
    first, cursor = await order_page(pk, page_limit=3, status="paid")
    assert [order.sk for order in first] == ["ORDER#003", "ORDER#004", "ORDER#005"]
    assert cursor is not None
    rest, cursor = await order_page(pk, cursor, page_limit=3, status="paid")
    assert [order.sk for order in rest] == ["ORDER#006"]
    assert cursor is None
    assert await order_page(pk, status="cancelled") == ([], None)


def sync_filtered_pages(customer_id: str) -> None:
    pk = seed(customer_id)
    first, cursor = sync_order_page(pk, page_limit=3, status="paid")
    assert [order.sk for order in first] == ["ORDER#003", "ORDER#004", "ORDER#005"]
    assert cursor is not None
    rest, cursor = sync_order_page(pk, cursor, page_limit=3, status="paid")
    assert [order.sk for order in rest] == ["ORDER#006"]
    assert cursor is None
    assert sync_order_page(pk, status="cancelled") == ([], None)


async def streaming(customer_id: str) -> None:
    pk = seed(customer_id)
    keys = []
    async for order in Order.query(partition_key=pk, page_size=2):
        keys.append(order.sk)
    assert keys == [f"ORDER#{i:03d}" for i in range(7)]


def sync_streaming(customer_id: str) -> None:
    pk = seed(customer_id)
    keys = []
    for order in Order.sync_query(partition_key=pk, page_size=2):
        keys.append(order.sk)
    assert keys == [f"ORDER#{i:03d}" for i in range(7)]


async def query_options(customer_id: str) -> None:
    pk = seed(customer_id)
    rows = [
        row
        async for row in Order.query(
            partition_key=pk,
            sort_key_condition=Order.sk.between("ORDER#001", "ORDER#005"),
            filter_condition=Order.status == "paid",
            scan_index_forward=False,
            fields=["pk", "sk", "status"],
            as_dict=True,
        )
    ]
    assert [row["sk"] for row in rows] == ["ORDER#005", "ORDER#004", "ORDER#003"]
    assert all(set(row) == {"pk", "sk", "status"} for row in rows)
    assert all(row["status"] == "paid" for row in rows)


def sync_query_options(customer_id: str) -> None:
    pk = seed(customer_id)
    rows = list(
        Order.sync_query(
            partition_key=pk,
            sort_key_condition=Order.sk.between("ORDER#001", "ORDER#005"),
            filter_condition=Order.status == "paid",
            scan_index_forward=False,
            fields=["pk", "sk", "status"],
            as_dict=True,
        )
    )
    assert [row["sk"] for row in rows] == ["ORDER#005", "ORDER#004", "ORDER#003"]
    assert all(set(row) == {"pk", "sk", "status"} for row in rows)
    assert all(row["status"] == "paid" for row in rows)


async def index_pages(customer_id: str) -> None:
    pk = seed(customer_id)
    index = Order.customer_status_index
    deadline = time.monotonic() + 5
    while True:
        visible = [order async for order in index.query(partition_key=f"{pk}#paid")]
        if len(visible) == 4:
            break
        if time.monotonic() >= deadline:
            raise AssertionError("Seeded orders did not become visible in the GSI")
        await asyncio.sleep(0.1)
    cursor = None
    keys = []
    for _ in range(10):
        result = index.query(
            partition_key=f"{pk}#paid",
            limit=3,
            page_size=1,
            last_evaluated_key=cursor,
        )
        keys.extend([order.sk async for order in result])
        cursor = result.last_evaluated_key
        if cursor is None:
            break
        assert {"pk", "sk", "customer_status"} <= cursor.keys()
    else:
        raise AssertionError("Index pagination did not exhaust")
    assert keys == ["ORDER#003", "ORDER#004", "ORDER#005", "ORDER#006"]


def sync_index_pages(customer_id: str) -> None:
    pk = seed(customer_id)
    index = Order.customer_status_index
    deadline = time.monotonic() + 5
    while True:
        visible = list(index.sync_query(partition_key=f"{pk}#paid"))
        if len(visible) == 4:
            break
        if time.monotonic() >= deadline:
            raise AssertionError("Seeded orders did not become visible in the GSI")
        time.sleep(0.1)
    cursor = None
    keys = []
    for _ in range(10):
        result = index.sync_query(
            partition_key=f"{pk}#paid",
            limit=3,
            page_size=1,
            scan_index_forward=False,
            last_evaluated_key=cursor,
        )
        keys.extend(order.sk for order in result)
        cursor = result.last_evaluated_key
        if cursor is None:
            break
        assert {"pk", "sk", "customer_status"} <= cursor.keys()
    else:
        raise AssertionError("Index pagination did not exhaust")
    assert keys == ["ORDER#006", "ORDER#005", "ORDER#004", "ORDER#003"]


async def scan_items(customer_id: str) -> None:
    pk = seed(customer_id)
    keys = set()
    async for row in Order.scan(filter_condition=Order.pk == pk, fields=["pk", "sk"], as_dict=True):
        keys.add(row["sk"])
        assert set(row) == {"pk", "sk"}
    assert keys == {f"ORDER#{i:03d}" for i in range(7)}


def sync_scan_items(customer_id: str) -> None:
    pk = seed(customer_id)
    keys = set()
    for row in Order.sync_scan(filter_condition=Order.pk == pk, fields=["pk", "sk"], as_dict=True):
        keys.add(row["sk"])
        assert set(row) == {"pk", "sk"}
    assert keys == {f"ORDER#{i:03d}" for i in range(7)}


async def async_examples() -> None:
    for operation in (
        pagination,
        filtered_pages,
        streaming,
        query_options,
        index_pages,
        scan_items,
    ):
        await operation(uuid4().hex)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-url", required=True, help="LocalStack endpoint")
    args = parser.parse_args()
    set_default_client(
        DynamoDBClient(
            region="us-east-1",
            endpoint_url=args.endpoint_url,
            access_key="testing",
            secret_key="testing",
        )
    )
    if not Order.sync_table_exists():
        Order.sync_create_table(wait=True)
    asyncio.run(async_examples())
    for operation in (
        sync_pagination,
        sync_filtered_pages,
        sync_streaming,
        sync_query_options,
        sync_index_pages,
        sync_scan_items,
    ):
        operation(uuid4().hex)
    print("All query examples passed.")


if __name__ == "__main__":
    main()
