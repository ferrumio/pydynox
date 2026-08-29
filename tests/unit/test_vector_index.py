"""Unit tests for VectorIndex."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import StringAttribute, VectorAttribute
from pydynox.indexes import VectorDistance, VectorIndex


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
        "partition_key": "tenant",
        "inline_filters": ["cat"],
        "projection": "INCLUDE",
        "non_key_attributes": ["name", "cat"],
    }


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
    vector, expression, names, values = Product.semantic._prepare_search(
        [1.0, 0.0, 0.0],
        "TENANT#1",
        Product.category == "books",
        5,
    )

    assert vector == [1.0, 0.0, 0.0]
    assert expression == "#vector_pk = :vector_pk AND #n1 = :v1"
    assert names == {"#vector_pk": "tenant", "#n1": "cat"}
    assert values == {":vector_pk": "TENANT#1", ":v1": "books"}


def test_model_create_table_includes_vector_indexes() -> None:
    client = MagicMock(spec=DynamoDBClient)
    with patch.object(Product, "_get_client", return_value=client):
        Product.sync_create_table()

    kwargs = client.sync_create_table.call_args.kwargs
    assert kwargs["vector_indexes"] == [Product.semantic.to_create_table_definition(Product)]


def test_model_rejects_provisioned_vector_table() -> None:
    client = MagicMock(spec=DynamoDBClient)
    with patch.object(Product, "_get_client", return_value=client):
        with pytest.raises(ValueError, match="PAY_PER_REQUEST"):
            Product.sync_create_table(billing_mode="PROVISIONED")
