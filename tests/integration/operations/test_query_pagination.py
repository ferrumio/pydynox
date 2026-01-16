"""Integration tests for query pagination behavior."""

import pytest


@pytest.fixture
def pagination_table(dynamo):
    """Create a table with 25 items for pagination tests."""
    for i in range(25):
        dynamo.put_item(
            "test_table",
            {"pk": "PAGE#1", "sk": f"ITEM#{i:03d}", "value": i},
        )
    return dynamo


def test_query_limit_stops_after_n_items(pagination_table):
    """Query with limit=10 returns exactly 10 items, not all items.

    GIVEN a table with 25 items
    WHEN querying with limit=10
    THEN exactly 10 items are returned (not all 25)
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            limit=10,
        )
    )

    assert len(items) == 10


def test_query_page_size_controls_dynamo_limit(pagination_table):
    """Query with page_size controls items per DynamoDB request.

    GIVEN a table with 25 items
    WHEN querying with page_size=5 (no limit)
    THEN all 25 items are returned (auto-pagination)
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            page_size=5,
        )
    )

    assert len(items) == 25


def test_query_limit_and_page_size_together(pagination_table):
    """Query with both limit and page_size works correctly.

    GIVEN a table with 25 items
    WHEN querying with limit=12 and page_size=5
    THEN exactly 12 items are returned (fetching 5 per page)
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            limit=12,
            page_size=5,
        )
    )

    assert len(items) == 12
    # Items should be in order
    assert items[0]["sk"] == "ITEM#000"
    assert items[11]["sk"] == "ITEM#011"


def test_query_no_limit_returns_all(pagination_table):
    """Query without limit returns all items via auto-pagination.

    GIVEN a table with 25 items
    WHEN querying without limit
    THEN all 25 items are returned
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
        )
    )

    assert len(items) == 25


def test_query_limit_greater_than_total(pagination_table):
    """Query with limit > total items returns all items.

    GIVEN a table with 25 items
    WHEN querying with limit=100
    THEN all 25 items are returned
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            limit=100,
        )
    )

    assert len(items) == 25


def test_query_limit_one(pagination_table):
    """Query with limit=1 returns exactly 1 item.

    GIVEN a table with 25 items
    WHEN querying with limit=1
    THEN exactly 1 item is returned
    """
    dynamo = pagination_table

    items = list(
        dynamo.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            limit=1,
        )
    )

    assert len(items) == 1
    assert items[0]["sk"] == "ITEM#000"


def test_query_manual_pagination_with_limit(pagination_table):
    """Manual pagination works correctly with limit.

    GIVEN a table with 25 items
    WHEN querying with limit=10 and using last_evaluated_key
    THEN can paginate through all items in chunks of 10
    """
    dynamo = pagination_table
    all_items = []

    # First page
    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "PAGE#1"},
        limit=10,
    )
    for item in result:
        all_items.append(item)

    assert len(all_items) == 10
    assert result.last_evaluated_key is not None

    # Second page
    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "PAGE#1"},
        limit=10,
        last_evaluated_key=result.last_evaluated_key,
    )
    for item in result:
        all_items.append(item)

    assert len(all_items) == 20

    # Third page (only 5 remaining)
    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "PAGE#1"},
        limit=10,
        last_evaluated_key=result.last_evaluated_key,
    )
    for item in result:
        all_items.append(item)

    assert len(all_items) == 25
    assert result.last_evaluated_key is None


def test_scan_limit_stops_after_n_items(pagination_table):
    """Scan with limit=10 returns exactly 10 items.

    GIVEN a table with 25 items
    WHEN scanning with limit=10
    THEN exactly 10 items are returned
    """
    dynamo = pagination_table

    items = list(
        dynamo.scan(
            "test_table",
            limit=10,
        )
    )

    assert len(items) == 10


def test_scan_page_size_returns_all(pagination_table):
    """Scan with page_size (no limit) returns all items matching filter.

    GIVEN a table with 25 items with pk=PAGE#1
    WHEN scanning with page_size=100 and filter for pk=PAGE#1
    THEN all 25 items are returned
    """
    dynamo = pagination_table

    # Use larger page_size to ensure we get all items in reasonable number of pages
    items = list(
        dynamo.scan(
            "test_table",
            filter_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
            page_size=100,
        )
    )

    assert len(items) == 25


def test_scan_no_limit_returns_all(pagination_table):
    """Scan without limit returns all items matching filter.

    GIVEN a table with 25 items with pk=PAGE#1
    WHEN scanning without limit and filter for pk=PAGE#1
    THEN all 25 items are returned
    """
    dynamo = pagination_table

    items = list(
        dynamo.scan(
            "test_table",
            filter_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": "PAGE#1"},
        )
    )

    assert len(items) == 25
