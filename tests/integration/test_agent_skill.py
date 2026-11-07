"""Run the consumer skill workflows through the SDK and LocalStack."""

import inspect
from uuid import uuid4

import pytest
from pydynox import ModelConfig, set_default_client


@pytest.mark.parametrize(
    "operation",
    [
        "crud",
        "sync_crud",
        "query_and_batch",
        "sync_query_and_batch",
        "pagination",
        "sync_pagination",
        "transaction",
        "sync_transaction",
    ],
)
async def test_agent_skill_localstack_examples(table, agent_skill_examples, operation):
    # GIVEN the skill model using the integration suite's DynamoDB table
    set_default_client(table)
    agent_skill_examples["Order"].model_config = ModelConfig(
        table="test_table", consistent_read=True
    )

    # WHEN a workflow runs against LocalStack with unique keys
    result = agent_skill_examples[operation](uuid4().hex)
    if inspect.isawaitable(result):
        await result
    # THEN the workflow's CRUD, pagination, batch, or transaction assertions passed


@pytest.mark.parametrize(
    "operation",
    [
        "pagination",
        "sync_pagination",
        "filtered_pages",
        "sync_filtered_pages",
        "streaming",
        "sync_streaming",
        "query_options",
        "sync_query_options",
        "index_pages",
        "sync_index_pages",
        "scan_items",
        "sync_scan_items",
    ],
)
async def test_agent_skill_query_recipes(table, agent_skill_query_examples, operation):
    # GIVEN a separate table with the example's actual GSI schema
    set_default_client(table)
    model = agent_skill_query_examples["Order"]
    if not model.sync_table_exists():
        model.sync_create_table(wait=True)

    # WHEN a recipe runs with data isolated by customer
    result = agent_skill_query_examples[operation](uuid4().hex)
    if inspect.isawaitable(result):
        await result
    # THEN it asserts complete pages, exact ordering/fields, or index/scan results
