"""Vector search tests for MemoryBackend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VectorAttribute
from pydynox.indexes import VectorDistance, VectorIndex
from pydynox.testing import MemoryBackend


class Product(Model):
    model_config = ModelConfig(table="vector-products")

    pk = StringAttribute(partition_key=True)
    tenant_id = StringAttribute()
    category = StringAttribute()
    embedding = VectorAttribute(dimensions=2)

    semantic = VectorIndex(
        index_name="semantic-index",
        vector_attribute="embedding",
        partition_key="tenant_id",
        inline_filters=["category"],
    )


class DotProductDocument(Model):
    model_config = ModelConfig(table="dot-documents")

    pk = StringAttribute(partition_key=True)
    embedding = VectorAttribute(dimensions=2)

    semantic = VectorIndex(
        index_name="dot-index",
        vector_attribute="embedding",
        distance=VectorDistance.DOT_PRODUCT,
    )


class EuclideanDocument(Model):
    model_config = ModelConfig(table="euclidean-documents")

    pk = StringAttribute(partition_key=True)
    title = StringAttribute()
    hidden = StringAttribute()
    embedding = VectorAttribute(dimensions=2)

    semantic = VectorIndex(
        index_name="euclidean-index",
        vector_attribute="embedding",
        distance=VectorDistance.EUCLIDEAN,
        projection=["title"],
    )


def test_sync_vector_search_orders_by_cosine_distance() -> None:
    with MemoryBackend():
        Product.sync_create_table()
        Product(
            pk="1",
            tenant_id="TENANT#1",
            category="books",
            embedding=[1.0, 0.0],
        ).sync_save()
        Product(
            pk="2",
            tenant_id="TENANT#1",
            category="books",
            embedding=[0.0, 1.0],
        ).sync_save()

        matches = Product.semantic.sync_search(
            [0.9, 0.1],
            partition_key="TENANT#1",
        )

        assert [match.item.pk for match in matches] == ["1", "2"]
        assert matches.metrics.items_count == 2
        assert matches.metrics.vector_search_bytes == 8.0


def test_vector_write_metrics() -> None:
    with MemoryBackend():
        Product.sync_create_table()
        product = Product(
            pk="1",
            tenant_id="TENANT#1",
            category="books",
            embedding=[1.0, 0.0],
        )

        product.sync_save()

        assert Product._get_client().get_last_metrics().vector_write_bytes == 8.0


@pytest.mark.asyncio
async def test_async_table_creation_registers_vector_index() -> None:
    with MemoryBackend():
        await Product.create_table(wait=True)

        info = await Product.semantic.describe()

        assert info.status == "ACTIVE"
        assert info.dimensions == 2


@pytest.mark.asyncio
async def test_async_vector_search_applies_inline_filter() -> None:
    with MemoryBackend():
        await Product.create_table()
        await Product(
            pk="book",
            tenant_id="TENANT#1",
            category="books",
            embedding=[1.0, 0.0],
        ).save()
        await Product(
            pk="music",
            tenant_id="TENANT#1",
            category="music",
            embedding=[1.0, 0.0],
        ).save()

        matches = await Product.semantic.search(
            [1.0, 0.0],
            partition_key="TENANT#1",
            where=Product.category == "books",
        )

        assert [match.item.pk for match in matches] == ["book"]


def test_vector_search_can_return_dicts() -> None:
    with MemoryBackend():
        Product.sync_create_table()
        Product(
            pk="1",
            tenant_id="TENANT#1",
            category="books",
            embedding=[1.0, 0.0],
        ).sync_save()

        matches = Product.semantic.sync_search(
            [1.0, 0.0],
            partition_key="TENANT#1",
            as_dict=True,
        )

        assert matches[0].item["pk"] == "1"
        assert "embedding" not in matches[0].item


def test_model_vector_search_explicitly_requests_vector_attribute() -> None:
    with MemoryBackend():
        Product.sync_create_table()
        Product(
            pk="1",
            tenant_id="TENANT#1",
            category="books",
            embedding=[1.0, 0.0],
        ).sync_save()

        matches = Product.semantic.sync_search(
            [1.0, 0.0],
            partition_key="TENANT#1",
        )

        assert matches[0].item.embedding == [1.0, 0.0]


def test_dot_product_search_orders_highest_score_first() -> None:
    with MemoryBackend():
        DotProductDocument.sync_create_table()
        DotProductDocument(pk="1", embedding=[1.0, 0.0]).sync_save()
        DotProductDocument(pk="2", embedding=[2.0, 0.0]).sync_save()

        matches = DotProductDocument.semantic.sync_search([1.0, 0.0])

        assert [match.item.pk for match in matches] == ["2", "1"]


def test_euclidean_search_applies_top_k_and_projection() -> None:
    with MemoryBackend():
        EuclideanDocument.sync_create_table()
        EuclideanDocument(
            pk="1",
            title="Closest",
            hidden="secret",
            embedding=[1.0, 0.0],
        ).sync_save()
        EuclideanDocument(
            pk="2",
            title="Farthest",
            hidden="secret",
            embedding=[3.0, 0.0],
        ).sync_save()

        matches = EuclideanDocument.semantic.sync_search(
            [0.9, 0.0],
            top_k=1,
            as_dict=True,
        )

        assert matches[0].item == {"pk": "1", "title": "Closest"}


def test_include_projection_can_build_partial_model() -> None:
    with MemoryBackend():
        EuclideanDocument.sync_create_table()
        EuclideanDocument(
            pk="1",
            title="Closest",
            hidden="secret",
            embedding=[1.0, 0.0],
        ).sync_save()

        matches = EuclideanDocument.semantic.sync_search([1.0, 0.0])

        assert matches[0].item.pk == "1"
        assert matches[0].item.title == "Closest"
        assert matches[0].item.embedding == [1.0, 0.0]
        assert matches[0].item.hidden is None


def test_empty_vector_index_returns_no_matches() -> None:
    with MemoryBackend():
        DotProductDocument.sync_create_table()
        matches = DotProductDocument.semantic.sync_search([1.0, 0.0])

        assert matches == []
        assert matches.metrics.items_count == 0


def test_vector_index_lifecycle_in_memory() -> None:
    with MemoryBackend():
        Product._get_client().sync_create_table(
            "vector-products",
            partition_key=("pk", "S"),
        )
        Product.semantic.sync_create(wait=True)
        info = Product.semantic.sync_describe()
        assert info.status == "ACTIVE"
        assert info.dimensions == 2
        with pytest.raises(ValueError, match="already exists"):
            Product.semantic.sync_create()
        Product.semantic.sync_delete(wait=True)
        with pytest.raises(ValueError, match="not found"):
            Product.semantic.sync_describe()
        with pytest.raises(ValueError, match="not found"):
            Product.semantic.sync_delete()


def test_vector_index_creation_requires_table() -> None:
    with MemoryBackend():
        with pytest.raises(ValueError, match="does not exist"):
            Product.semantic.sync_create()


def test_vector_index_is_not_auto_discovered() -> None:
    with MemoryBackend():
        Product._get_client().sync_create_table(
            "vector-products",
            partition_key=("pk", "S"),
        )

        with pytest.raises(ValueError, match="not found"):
            Product.semantic.sync_search(
                [1.0, 0.0],
                partition_key="TENANT#1",
                as_dict=True,
            )

        with pytest.raises(ValueError, match="not found"):
            Product.semantic.sync_describe()
