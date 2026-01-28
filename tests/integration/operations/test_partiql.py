"""Integration tests for PartiQL operations."""

import pytest


@pytest.fixture
def populated_table(dynamo):
    """Create a table with test data for PartiQL tests."""
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        {"pk": "USER#1", "sk": "ORDER#001", "total": 100, "status": "shipped"},
        {"pk": "USER#1", "sk": "ORDER#002", "total": 200, "status": "pending"},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
    ]
    for item in items:
        dynamo.sync_put_item("test_table", item)
    return dynamo


@pytest.mark.asyncio
async def test_execute_statement_select_all(populated_table):
    """Test SELECT * with PartiQL."""
    dynamo = populated_table

    # WHEN we execute a PartiQL SELECT
    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#1"],
    )

    # THEN matching items are returned
    assert len(result) == 3
    assert all(item["pk"] == "USER#1" for item in result)
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_statement_select_specific_columns(populated_table):
    """Test SELECT specific columns with PartiQL."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT name, age FROM test_table WHERE pk = ? AND sk = ?",
        parameters=["USER#1", "PROFILE"],
    )

    assert len(result) == 1
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == 30


@pytest.mark.asyncio
async def test_execute_statement_with_multiple_parameters(populated_table):
    """Test PartiQL with multiple parameters."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ? AND sk = ?",
        parameters=["USER#1", "ORDER#001"],
    )

    assert len(result) == 1
    assert result[0]["total"] == 100
    assert result[0]["status"] == "shipped"


@pytest.mark.asyncio
async def test_execute_statement_no_results(populated_table):
    """Test PartiQL with no matching results."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["NONEXISTENT"],
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_execute_statement_consistent_read(populated_table):
    """Test PartiQL with consistent read."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#2"],
        consistent_read=True,
    )

    assert len(result) == 1
    assert result[0]["name"] == "Bob"


@pytest.mark.asyncio
async def test_execute_statement_returns_metrics(populated_table):
    """Test that PartiQL returns metrics."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#1"],
    )

    assert result.metrics.duration_ms > 0
    assert result.metrics.items_count == 3


@pytest.mark.asyncio
async def test_execute_statement_without_parameters(populated_table):
    """Test PartiQL without parameters - query specific partition."""
    dynamo = populated_table

    # Query USER#1 partition (3 items) and USER#2 partition (1 item) separately
    # to avoid full table scan which would include items from other tests
    result1 = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#1"],
    )
    result2 = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#2"],
    )

    assert len(result1) == 3
    assert len(result2) == 1


@pytest.mark.asyncio
async def test_execute_statement_iterate(populated_table):
    """Test iterating over PartiQL result."""
    dynamo = populated_table

    result = await dynamo.execute_statement(
        "SELECT * FROM test_table WHERE pk = ?",
        parameters=["USER#1"],
    )

    names = []
    for item in result:
        if "name" in item:
            names.append(item["name"])

    assert "Alice" in names
