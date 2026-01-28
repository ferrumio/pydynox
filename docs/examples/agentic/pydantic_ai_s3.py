"""Pydantic AI async CRUD with S3 example."""

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, S3Attribute, S3File, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    title = StringAttribute()
    author = StringAttribute()
    size_bytes = NumberAttribute(default=0)
    content = S3Attribute(bucket="my-docs-bucket", prefix="documents/")


model = BedrockConverseModel(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
)

agent = Agent(model, system_prompt="You are a document assistant.")


@agent.tool
async def upload_document(
    ctx,
    doc_id: str,
    title: str,
    author: str,
    content: str,
    version: str = "1",
) -> dict:
    """Upload a new document to S3."""
    content_bytes = content.encode("utf-8")

    doc = Document(
        pk=f"DOC#{doc_id}",
        sk=f"VERSION#{version}",
        title=title,
        author=author,
        size_bytes=len(content_bytes),
    )
    doc.content = S3File(content_bytes, name=f"{doc_id}.txt", content_type="text/plain")
    await doc.save()

    return {
        "success": True,
        "doc_id": doc_id,
        "s3_key": doc.content.key,
    }


@agent.tool
async def get_document(ctx, doc_id: str, version: str = "latest") -> dict:
    """Get document details."""
    if version == "latest":
        docs = [
            doc
            async for doc in Document.query(
                key_condition="pk = :pk",
                expression_values={":pk": f"DOC#{doc_id}"},
                scan_index_forward=False,
                limit=1,
            )
        ]
        if not docs:
            return {"error": f"Document {doc_id} not found"}
        doc = docs[0]
    else:
        doc = await Document.get(pk=f"DOC#{doc_id}", sk=f"VERSION#{version}")
        if not doc:
            return {"error": f"Document {doc_id} version {version} not found"}

    return {
        "doc_id": doc_id,
        "version": doc.sk.replace("VERSION#", ""),
        "title": doc.title,
        "size_kb": round(doc.size_bytes / 1024, 2),
    }
