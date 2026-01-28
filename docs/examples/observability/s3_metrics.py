"""Example: S3 metrics in Model observability.

Shows how to track S3 upload/download metrics when using S3Attribute.
"""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox._internal._s3 import S3File
from pydynox.attributes import S3Attribute, StringAttribute

# Create client
client = DynamoDBClient(region="us-east-1")


class Document(Model):
    """Document model with S3 content."""

    model_config = ModelConfig(table="documents", client=client)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket", prefix="docs/")


async def main():
    # Reset metrics
    Document.reset_metrics()

    # Save document with S3 content
    doc = Document(pk="DOC#1", sk="v1", name="report.pdf")
    doc.content = S3File(b"PDF content here...", name="report.pdf")
    await doc.save()

    # Check S3 metrics
    metrics = Document.get_total_metrics()

    print("=== S3 Metrics ===")
    print(f"S3 duration: {metrics.s3_duration_ms:.2f} ms")
    print(f"S3 API calls: {metrics.s3_calls}")
    print(f"Bytes uploaded: {metrics.s3_bytes_uploaded}")
    print(f"Bytes downloaded: {metrics.s3_bytes_downloaded}")

    # Combined with DynamoDB metrics
    print("\n=== All Metrics ===")
    print(f"Total duration: {metrics.total_duration_ms:.2f} ms")
    print(f"DynamoDB operations: {metrics.operation_count}")
    print(f"RCU consumed: {metrics.total_rcu}")
    print(f"WCU consumed: {metrics.total_wcu}")


asyncio.run(main())
