import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import CompressedAttribute, StringAttribute


class Article(Model):
    model_config = ModelConfig(table="articles")

    pk = StringAttribute(partition_key=True)
    content = CompressedAttribute()  # Auto-compresses large text


async def main():
    # Create an article with large content
    article = Article(
        pk="ARTICLE#123",
        content="This is a very long article..." * 1000,
    )
    await article.save()

    # When you read it back, it's automatically decompressed
    loaded = await Article.get(pk="ARTICLE#123")
    print(loaded.content)  # Original text, not compressed


asyncio.run(main())
