import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    content = StringAttribute()
    version = VersionAttribute()


async def main():
    # Create new document
    doc = Document(pk="DOC#VERSION", content="Hello")
    print(doc.version)  # None

    await doc.save()
    print(doc.version)  # 1

    # Update document
    doc.content = "Hello World"
    await doc.save()
    print(doc.version)  # 2

    # Load from DB - version is preserved
    loaded = await Document.get(pk="DOC#VERSION")
    print(loaded.version)  # 2


asyncio.run(main())
