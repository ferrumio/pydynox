"""Pydantic AI dependencies example."""

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    title = StringAttribute()
    author = StringAttribute()


@dataclass
class AppDeps:
    client: DynamoDBClient
    cache: dict  # Simple in-memory cache


model = BedrockConverseModel(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
)

agent = Agent(model, deps_type=AppDeps, system_prompt="You are a document assistant.")


@agent.tool
async def get_document_cached(ctx, doc_id: str) -> dict:
    """Get document with caching."""
    cache_key = f"doc:{doc_id}"

    if cache_key in ctx.deps.cache:
        return ctx.deps.cache[cache_key]

    doc = await Document.get(pk=f"DOC#{doc_id}", sk="VERSION#latest")
    if doc:
        result = {"title": doc.title, "author": doc.author}
        ctx.deps.cache[cache_key] = result
        return result

    return {"error": "Not found"}


@agent.tool
async def safe_delete(ctx, doc_id: str) -> dict:
    """Safely delete a document."""
    try:
        doc = await Document.get(pk=f"DOC#{doc_id}", sk="VERSION#latest")
        if not doc:
            return {"success": False, "error": "Not found"}

        await doc.delete()
        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}
