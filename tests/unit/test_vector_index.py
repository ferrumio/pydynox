"""Unit tests for VectorIndex."""

from datetime import datetime, timezone
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, pydynox_core
from pydynox.attributes import (
    BooleanAttribute,
    DatetimeAttribute,
    EnumAttribute,
    StringAttribute,
    VectorAttribute,
)
from pydynox.exceptions import ValidationException
from pydynox.indexes import VectorDistance, VectorIndex, VectorMatch, VectorSearchResult


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)
    tenant_id = StringAttribute(alias="tenant")
    category = StringAttribute(alias="cat")
    name = StringAttribute()
    embedding = VectorAttribute(dimensions=3, alias="emb")

    semantic = VectorIndex(
        index_name="semantic-index",
        vector_attribute="embedding",
        distance=VectorDistance.COSINE,
        partition_key="tenant_id",
        inline_filters=["category"],
        projection=["name", "category"],
    )


def test_vector_index_is_collected_and_bound() -> None:
    assert Product._vector_indexes["semantic"] is Product.semantic
    assert Product.semantic._model_class is Product


def test_vector_index_create_table_definition_uses_aliases() -> None:
    assert Product.semantic.to_create_table_definition(Product) == {
        "index_name": "semantic-index",
        "vector_attribute": "emb",
        "dimensions": 3,
        "distance_function": "COSINE",
        "attribute_definitions": [("tenant", "S"), ("cat", "S")],
        "table_key_attributes": ["pk"],
        "partition_key": "tenant",
        "inline_filters": ["cat"],
        "projection": "INCLUDE",
        "non_key_attributes": ["name", "cat"],
    }


def test_client_definition_requires_search_schema_attribute_types() -> None:
    client = pydynox_core.DynamoDBClient(
        region="us-east-1",
        access_key="testing",
        secret_key="testing",
    )
    with pytest.raises(ValidationException, match="missing from attribute_definitions"):
        client.create_vector_index(
            "products",
            {
                "index_name": "semantic-index",
                "vector_attribute": "embedding",
                "dimensions": 3,
                "distance_function": "COSINE",
                "partition_key": "tenant_id",
                "projection": "ALL",
            },
        )


def test_vector_index_requires_vector_attribute() -> None:
    with pytest.raises(ValueError, match="must be a VectorAttribute"):

        class Invalid(Model):
            model_config = ModelConfig(table="invalid")
            pk = StringAttribute(partition_key=True)
            embedding = StringAttribute()
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="embedding",
            )


def test_vector_index_validates_constructor_arguments() -> None:
    with pytest.raises(ValueError, match="index_name is required"):
        VectorIndex(index_name="", vector_attribute="embedding")
    with pytest.raises(ValueError, match="vector_attribute is required"):
        VectorIndex(index_name="semantic-index", vector_attribute="")
    with pytest.raises(ValueError, match="at most 18 inline filters"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            inline_filters=[f"filter_{index}" for index in range(19)],
        )
    with pytest.raises(ValueError, match="duplicate inline filters"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            inline_filters=["category", "category"],
        )
    with pytest.raises(ValueError, match="both partition key and inline filter"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            partition_key="tenant",
            inline_filters=["tenant"],
        )
    with pytest.raises(ValueError, match="projection must be"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            projection="INVALID",
        )


def test_unbound_vector_index_rejects_model_operations() -> None:
    index = VectorIndex(index_name="semantic-index", vector_attribute="embedding")
    with pytest.raises(RuntimeError, match="not bound to a model"):
        index.sync_search([1.0, 0.0])


def test_vector_index_validates_referenced_attributes() -> None:
    with pytest.raises(ValueError, match="unknown attribute 'missing'"):

        class UnknownVector(Model):
            model_config = ModelConfig(table="unknown-vector")
            pk = StringAttribute(partition_key=True)
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="missing",
            )

    with pytest.raises(ValueError, match="cannot use its vector attribute as the partition key"):

        class VectorPartition(Model):
            model_config = ModelConfig(table="vector-partition")
            pk = StringAttribute(partition_key=True)
            embedding = VectorAttribute(dimensions=3)
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="embedding",
                partition_key="embedding",
            )

    with pytest.raises(ValueError, match="cannot use its vector attribute as an inline filter"):

        class VectorFilter(Model):
            model_config = ModelConfig(table="vector-filter")
            pk = StringAttribute(partition_key=True)
            embedding = VectorAttribute(dimensions=3)
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="embedding",
                inline_filters=["embedding"],
            )

    with pytest.raises(ValueError, match="unknown attribute 'missing'"):

        class UnknownProjection(Model):
            model_config = ModelConfig(table="unknown-projection")
            pk = StringAttribute(partition_key=True)
            embedding = VectorAttribute(dimensions=3)
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="embedding",
                projection=["missing"],
            )


def test_vector_index_requires_scalar_search_schema_attributes() -> None:
    with pytest.raises(ValueError, match="must use scalar DynamoDB type"):

        class Invalid(Model):
            model_config = ModelConfig(table="invalid-filter")
            pk = StringAttribute(partition_key=True)
            filter_flag = BooleanAttribute()
            embedding = VectorAttribute(dimensions=3)
            semantic = VectorIndex(
                index_name="semantic-index",
                vector_attribute="embedding",
                inline_filters=["filter_flag"],
            )


def test_inherited_vector_index_is_bound_independently() -> None:
    class BaseProduct(Model):
        model_config = ModelConfig(table="base-products")
        pk = StringAttribute(partition_key=True)
        embedding = VectorAttribute(dimensions=3)
        semantic = VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
        )

    class ChildProduct(BaseProduct):
        model_config = ModelConfig(table="child-products")

    assert BaseProduct.semantic is not ChildProduct.semantic
    assert BaseProduct.semantic._model_class is BaseProduct
    assert ChildProduct.semantic._model_class is ChildProduct


def test_inherited_vector_index_can_be_shadowed() -> None:
    class BaseProduct(Model):
        model_config = ModelConfig(table="base-products-shadowed")
        pk = StringAttribute(partition_key=True)
        embedding = VectorAttribute(dimensions=3)
        semantic = VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
        )

    class ChildProduct(BaseProduct):
        model_config = ModelConfig(table="child-products-shadowed")
        semantic = None

    assert "semantic" not in ChildProduct._vector_indexes
    assert ChildProduct.semantic is None
    assert BaseProduct.semantic._model_class is BaseProduct


def test_vector_index_rejects_invalid_projection() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            projection=[],
        )

    with pytest.raises(ValueError, match="duplicate projection attributes"):
        VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
            projection=["name", "name"],
        )


def test_vector_index_validates_top_k_and_partition_key() -> None:
    with pytest.raises(ValueError, match="requires partition_key"):
        Product.semantic.sync_search([1.0, 0.0, 0.0])

    with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
        Product.semantic.sync_search(
            [1.0, 0.0, 0.0],
            partition_key="TENANT#1",
            top_k=0,
        )

    class GlobalProduct(Model):
        model_config = ModelConfig(table="global-products")
        pk = StringAttribute(partition_key=True)
        embedding = VectorAttribute(dimensions=3)
        semantic = VectorIndex(
            index_name="semantic-index",
            vector_attribute="embedding",
        )

    with pytest.raises(ValueError, match="does not define a partition key"):
        GlobalProduct.semantic.sync_search(
            [1.0, 0.0, 0.0],
            partition_key="unexpected",
        )


def test_vector_index_validates_inline_filters() -> None:
    with pytest.raises(ValueError, match="equality comparisons joined by AND"):
        Product.semantic.sync_search(
            [1.0, 0.0, 0.0],
            partition_key="TENANT#1",
            where=Product.category.begins_with("book"),
        )

    with pytest.raises(ValueError, match="is not declared as an inline filter"):
        Product.semantic.sync_search(
            [1.0, 0.0, 0.0],
            partition_key="TENANT#1",
            where=Product.name == "Book",
        )


def test_vector_index_builds_partition_and_filter_expression() -> None:
    vector, expression, names, values, projection = Product.semantic._prepare_search(
        [1.0, 0.0, 0.0],
        "TENANT#1",
        Product.category == "books",
        5,
        as_dict=True,
    )

    assert vector == [1.0, 0.0, 0.0]
    assert expression == "#vector_pk = :vector_pk AND #n1 = :v1"
    assert names == {"#vector_pk": "tenant", "#n1": "cat"}
    assert values == {":vector_pk": "TENANT#1", ":v1": "books"}
    assert projection is None


def test_vector_index_serializes_multiple_inline_filters() -> None:
    vector, expression, names, values, _ = Product.semantic._prepare_search(
        [1.0, 0.0, 0.0],
        "TENANT#1",
        (Product.category == "books") & (Product.category == "reference"),
        5,
        as_dict=True,
    )

    assert vector == [1.0, 0.0, 0.0]
    assert expression == "#vector_pk = :vector_pk AND (#n1 = :v1 AND #n1 = :v2)"
    assert names == {"#vector_pk": "tenant", "#n1": "cat"}
    assert values == {
        ":vector_pk": "TENANT#1",
        ":v1": "books",
        ":v2": "reference",
    }


def test_model_search_builds_explicit_projection() -> None:
    _, _, names, _, projection = Product.semantic._prepare_search(
        [1.0, 0.0, 0.0],
        "TENANT#1",
        None,
        5,
    )

    assert names is not None
    assert projection is not None
    projected_names = {names[placeholder] for placeholder in projection.split(", ")}
    assert projected_names == {"pk", "tenant", "cat", "name", "emb"}


def test_vector_index_serializes_partition_and_filter_values() -> None:
    class Segment(Enum):
        PREMIUM = "premium"

    class Event(Model):
        model_config = ModelConfig(table="events")
        pk = StringAttribute(partition_key=True)
        occurred_at = DatetimeAttribute()
        segment = EnumAttribute(Segment)
        embedding = VectorAttribute(dimensions=2)
        semantic = VectorIndex(
            index_name="event-index",
            vector_attribute="embedding",
            partition_key="occurred_at",
            inline_filters=["segment"],
        )

    occurred_at = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    _, _, _, values, _ = Event.semantic._prepare_search(
        [1.0, 0.0],
        occurred_at,
        Event.segment == Segment.PREMIUM,
        5,
        as_dict=True,
    )

    assert values == {
        ":vector_pk": "2026-08-29T12:00:00+00:00",
        ":v1": "premium",
    }


def test_vector_index_rejects_model_result_when_required_attributes_are_unavailable() -> None:
    class Document(Model):
        model_config = ModelConfig(table="required-documents")
        pk = StringAttribute(partition_key=True)
        title = StringAttribute(required=True)
        embedding = VectorAttribute(dimensions=2)
        semantic = VectorIndex(
            index_name="document-index",
            vector_attribute="embedding",
            projection="KEYS_ONLY",
        )

    with pytest.raises(ValueError, match="required model attributes: title"):
        Document.semantic.sync_search([1.0, 0.0])


def test_model_create_table_includes_vector_indexes() -> None:
    client = MagicMock(spec=DynamoDBClient)
    with patch.object(Product, "_get_client", return_value=client):
        Product.sync_create_table()

    kwargs = client.sync_create_table.call_args.kwargs
    assert kwargs["vector_indexes"] == [Product.semantic.to_create_table_definition(Product)]
    assert kwargs["timeout_seconds"] is None


def test_vector_index_lifecycle_forwards_timeout() -> None:
    client = MagicMock(spec=DynamoDBClient)
    with patch.object(Product, "_get_client", return_value=client):
        Product.semantic.sync_create(wait=True, timeout_seconds=42)
        Product.semantic.sync_delete(wait=True, timeout_seconds=21)

    client.sync_create_vector_index.assert_called_once_with(
        "products",
        Product.semantic.to_create_table_definition(Product),
        wait=True,
        timeout_seconds=42,
    )
    client.sync_delete_vector_index.assert_called_once_with(
        "products",
        "semantic-index",
        wait=True,
        timeout_seconds=21,
    )


@pytest.mark.asyncio
async def test_async_vector_search_and_lifecycle() -> None:
    client = MagicMock(spec=DynamoDBClient)
    client.create_vector_index = AsyncMock()
    client.describe_vector_index = AsyncMock()
    client.delete_vector_index = AsyncMock()
    metrics = pydynox_core.OperationMetrics()
    client.search_vectors.return_value = VectorSearchResult(
        [
            VectorMatch(
                item={
                    "pk": "PRODUCT#1",
                    "tenant": "TENANT#1",
                    "cat": "books",
                    "name": "Book",
                    "emb": [1.0, 0.0, 0.0],
                },
                score=0.1,
            )
        ],
        metrics,
    )
    client.describe_vector_index.return_value = {
        "index_name": "semantic-index",
        "status": "ACTIVE",
        "backfilling": False,
        "item_count": 1,
        "size_bytes": 12,
        "index_arn": "arn:index",
        "dimensions": 3,
        "distance": "COSINE",
    }

    with patch.object(Product, "_get_client", return_value=client):
        matches = await Product.semantic.search(
            [1.0, 0.0, 0.0],
            partition_key="TENANT#1",
        )
        await Product.semantic.create(wait=True, timeout_seconds=42)
        info = await Product.semantic.describe()
        await Product.semantic.delete(wait=True, timeout_seconds=21)

    assert matches[0].item.pk == "PRODUCT#1"
    assert matches.metrics is metrics
    assert info.status == "ACTIVE"
    assert info.distance is VectorDistance.COSINE
    client.create_vector_index.assert_awaited_once()
    client.describe_vector_index.assert_awaited_once_with("products", "semantic-index")
    client.delete_vector_index.assert_awaited_once_with(
        "products",
        "semantic-index",
        wait=True,
        timeout_seconds=21,
    )


def test_model_rejects_provisioned_vector_table() -> None:
    client = MagicMock(spec=DynamoDBClient)
    with patch.object(Product, "_get_client", return_value=client):
        with pytest.raises(ValueError, match="PAY_PER_REQUEST"):
            Product.sync_create_table(billing_mode="PROVISIONED")
