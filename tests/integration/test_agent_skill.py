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
