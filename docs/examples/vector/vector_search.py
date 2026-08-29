"""Store embeddings and run a filtered vector search."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VectorAttribute
from pydynox.indexes import VectorDistance, VectorIndex


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)
    tenant_id = StringAttribute()
    category = StringAttribute()
    language = StringAttribute()
    name = StringAttribute()
    embedding = VectorAttribute(dimensions=3, required=True)

    semantic = VectorIndex(
        index_name="semantic-index",
        vector_attribute="embedding",
        distance=VectorDistance.COSINE,
        partition_key="tenant_id",
        inline_filters=["category", "language"],
        projection=["name", "category", "language"],
    )


async def main() -> None:
    query_vector = [0.12, -0.44, 0.91]
    matches = await Product.semantic.search(
        query_vector,
        partition_key="TENANT#acme",
        where=(Product.category == "books") & (Product.language == "en"),
        top_k=10,
        as_dict=True,
    )

    for match in matches:
        print(match.item["name"], match.score)

    print(matches.metrics.vector_search_bytes)


if __name__ == "__main__":
    asyncio.run(main())
