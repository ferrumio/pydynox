import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    content = StringAttribute()
    version = VersionAttribute()


async def main():
    # Create document
    doc = Document(pk="DOC#CONCURRENT", content="Original")
    await doc.save()

    # Two processes load the same document
    process_a = await Document.get(pk="DOC#CONCURRENT")
    process_b = await Document.get(pk="DOC#CONCURRENT")

    # Both have version 1
    print(process_a.version)  # 1
    print(process_b.version)  # 1

    # Process A updates first - succeeds
    process_a.content = "Updated by A"
    await process_a.save()
    print(process_a.version)  # 2

    # Process B tries to update - fails!
    process_b.content = "Updated by B"
    try:
        await process_b.save()
    except ConditionalCheckFailedException:
        print("Conflict! Someone else updated the document.")


asyncio.run(main())
