"""Pydantic AI integration with pydynox.

Use case: Document management agent with S3 storage.
Uses async methods for better performance.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, S3Attribute, S3File, StringAttribute

# Create client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


# Define models
class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)  # DOC#<id>
    sk = StringAttribute(range_key=True)  # VERSION#<version>
    title = StringAttribute()
    author = StringAttribute()
    size_bytes = NumberAttribute(default=0)
    content = S3Attribute(bucket="my-docs-bucket", prefix="documents/")


class Project(Model):
    model_config = ModelConfig(table="projects")

    pk = StringAttribute(hash_key=True)  # PROJECT#<id>
    sk = StringAttribute(range_key=True)  # METADATA
    name = StringAttribute()
    owner = StringAttribute()
    doc_count = NumberAttribute(default=0)


# Dependencies for the agent
@dataclass
class DocAgentDeps:
    """Dependencies passed to all tools."""

    client: DynamoDBClient


# Create the agent with Bedrock
model = BedrockConverseModel(
    model_name="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

agent = Agent(
    model,
    deps_type=DocAgentDeps,
    system_prompt="""You are a document management assistant.
You can search documents, get document info, and manage projects.
Always provide clear information about document sizes and versions.""",
)


@agent.tool
async def search_documents(ctx, query: str, limit: int = 10) -> list:
    """Search documents by title.

    Args:
        ctx: The run context with dependencies.
        query: Search term to match in document titles.
        limit: Maximum results to return.

    Returns:
        List of matching documents with title, author, and size.
    """
    scan_result = Document.async_scan(
        filter_condition=Document.title.contains(query),
        limit=limit,
    )
    docs = [doc async for doc in scan_result]

    return [
        {
            "doc_id": doc.pk.replace("DOC#", ""),
            "title": doc.title,
            "author": doc.author,
            "size_kb": round(doc.size_bytes / 1024, 2),
        }
        for doc in docs
    ]


@agent.tool
async def get_document(ctx, doc_id: str, version: str = "latest") -> dict:
    """Get document details and download URL.

    Args:
        ctx: The run context with dependencies.
        doc_id: The document ID.
        version: Version number or "latest".

    Returns:
        Document info with download URL.
    """
    if version == "latest":
        query_result = Document.async_query(
            hash_key=f"DOC#{doc_id}",
            scan_index_forward=False,
            limit=1,
        )
        docs = [doc async for doc in query_result]
        if not docs:
            return {"error": f"Document {doc_id} not found"}
        doc = docs[0]
    else:
        doc = await Document.async_get(pk=f"DOC#{doc_id}", sk=f"VERSION#{version}")
        if not doc:
            return {"error": f"Document {doc_id} version {version} not found"}

    return {
        "doc_id": doc_id,
        "version": doc.sk.replace("VERSION#", ""),
        "title": doc.title,
        "author": doc.author,
        "size_kb": round(doc.size_bytes / 1024, 2),
        "s3_key": doc.content.key if doc.content else None,
    }


@agent.tool
async def list_document_versions(ctx, doc_id: str) -> list:
    """List all versions of a document.

    Args:
        ctx: The run context with dependencies.
        doc_id: The document ID.

    Returns:
        List of versions with size and author.
    """
    query_result = Document.async_query(
        hash_key=f"DOC#{doc_id}",
        scan_index_forward=False,
    )
    docs = [doc async for doc in query_result]

    return [
        {
            "version": doc.sk.replace("VERSION#", ""),
            "author": doc.author,
            "size_kb": round(doc.size_bytes / 1024, 2),
        }
        for doc in docs
    ]


@agent.tool
async def get_project_stats(ctx, project_id: str) -> dict:
    """Get project statistics.

    Args:
        ctx: The run context with dependencies.
        project_id: The project ID.

    Returns:
        Project info with document count.
    """
    project = await Project.async_get(pk=f"PROJECT#{project_id}", sk="METADATA")

    if not project:
        return {"error": f"Project {project_id} not found"}

    return {
        "project_id": project_id,
        "name": project.name,
        "owner": project.owner,
        "document_count": project.doc_count,
    }


@agent.tool
async def upload_document(
    ctx,
    doc_id: str,
    title: str,
    author: str,
    content: str,
    version: str = "1",
) -> dict:
    """Upload a new document.

    Args:
        ctx: The run context with dependencies.
        doc_id: The document ID.
        title: Document title.
        author: Author name.
        content: Document content as text.
        version: Version number.

    Returns:
        Upload confirmation with S3 location.
    """
    content_bytes = content.encode("utf-8")

    doc = Document(
        pk=f"DOC#{doc_id}",
        sk=f"VERSION#{version}",
        title=title,
        author=author,
        size_bytes=len(content_bytes),
    )
    doc.content = S3File(content_bytes, name=f"{doc_id}.txt", content_type="text/plain")
    await doc.async_save()

    return {
        "success": True,
        "doc_id": doc_id,
        "version": version,
        "s3_key": doc.content.key,
        "size_kb": round(len(content_bytes) / 1024, 2),
    }


# Example usage
if __name__ == "__main__":
    import asyncio

    def create_tables():
        """Create DynamoDB tables if they don't exist."""
        if not client.table_exists("documents"):
            client.create_table(
                table_name="documents",
                hash_key=("pk", "S"),
                range_key=("sk", "S"),
                wait=True,
            )
            print("Table 'documents' created!")

        if not client.table_exists("projects"):
            client.create_table(
                table_name="projects",
                hash_key=("pk", "S"),
                range_key=("sk", "S"),
                wait=True,
            )
            print("Table 'projects' created!")

    async def seed_data():
        """Insert sample documents for testing."""
        sample_docs = [
            Document(
                pk="DOC#001",
                sk="VERSION#1",
                title="Q1 2025 quarterly report",
                author="Maria Silva",
                size_bytes=15360,
            ),
            Document(
                pk="DOC#001",
                sk="VERSION#2",
                title="Q1 2025 quarterly report - revised",
                author="Maria Silva",
                size_bytes=18432,
            ),
            Document(
                pk="DOC#002",
                sk="VERSION#1",
                title="Q4 2024 quarterly report",
                author="João Santos",
                size_bytes=12288,
            ),
            Document(
                pk="DOC#003",
                sk="VERSION#1",
                title="Annual budget proposal",
                author="Ana Costa",
                size_bytes=25600,
            ),
        ]

        sample_projects = [
            Project(
                pk="PROJECT#finance",
                sk="METADATA",
                name="Finance Reports",
                owner="Maria Silva",
                doc_count=3,
            ),
        ]

        for doc in sample_docs:
            await doc.async_save()
        for proj in sample_projects:
            await proj.async_save()

        print("Sample data inserted!")

    async def main():
        # Create tables first
        create_tables()

        # Seed data
        await seed_data()

        deps = DocAgentDeps(client=client)

        result = await agent.run(
            "Find all documents about 'quarterly report' and show me the latest version",
            deps=deps,
        )
        print(result.response)

    asyncio.run(main())
