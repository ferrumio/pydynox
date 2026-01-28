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
    # Create and update document
    doc = Document(pk="DOC#DELETE", content="Hello")
    await doc.save()
    doc.content = "Updated"
    await doc.save()
    print(f"Version: {doc.version}")  # 2

    # Load stale copy
    stale = await Document.get(pk="DOC#DELETE")

    # Update again
    doc.content = "Updated again"
    await doc.save()
    print(f"Version: {doc.version}")  # 3

    # Try to delete with stale version - fails!
    try:
        await stale.delete()
    except ConditionalCheckFailedException:
        print("Can't delete - version mismatch")

    # Delete with current version - succeeds
    await doc.delete()
    print("Deleted successfully")


asyncio.run(main())
