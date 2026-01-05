"""S3Attribute for storing large files in S3."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydynox._internal._s3 import S3File, S3Operations, S3Value
from pydynox.attributes.base import Attribute

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient


class S3Attribute(Attribute[S3Value | None]):
    """Attribute that stores large files in S3.

    The file is uploaded to S3 on save, and metadata is stored in DynamoDB.
    On read, returns an S3Value with methods to download or get presigned URL.

    Example:
        class Document(Model):
            model_config = ModelConfig(table="documents")

            pk = StringAttribute(hash_key=True)
            name = StringAttribute()
            content = S3Attribute(bucket="my-bucket", prefix="docs/")

        # Upload
        doc = Document(pk="DOC#1", name="report.pdf")
        doc.content = S3File(b"...", name="report.pdf", content_type="application/pdf")
        doc.save()

        # Download
        doc = Document.get(pk="DOC#1")
        data = doc.content.get_bytes()
        url = doc.content.presigned_url(3600)
    """

    attr_type: str = "M"  # Stored as Map in DynamoDB

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str | None = None,
        hash_key: bool = False,
        range_key: bool = False,
        default: S3Value | None = None,
        null: bool = True,
    ):
        """Create an S3Attribute.

        Args:
            bucket: S3 bucket name.
            prefix: Key prefix for uploaded files.
            region: S3 region (optional, inherits from DynamoDB client).
            hash_key: Not supported for S3Attribute.
            range_key: Not supported for S3Attribute.
            default: Default value (usually None).
            null: Whether None is allowed.
        """
        if hash_key or range_key:
            raise ValueError("S3Attribute cannot be a hash_key or range_key")

        super().__init__(hash_key=False, range_key=False, default=default, null=null)
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self.region = region
        self._s3_ops: S3Operations | None = None

    def _get_s3_ops(self, client: DynamoDBClient) -> S3Operations:
        """Get or create S3Operations from DynamoDB client config."""
        if self._s3_ops is None:
            # Get config from DynamoDB client
            config = client._get_client_config()

            # Helper to safely get string values
            def get_str(key: str) -> str | None:
                val = config.get(key)
                return str(val) if val is not None else None

            # Helper to safely get float values
            def get_float(key: str) -> float | None:
                val = config.get(key)
                return float(val) if val is not None else None

            # Helper to safely get int values
            def get_int(key: str) -> int | None:
                val = config.get(key)
                return int(val) if val is not None else None

            self._s3_ops = S3Operations(
                region=self.region or get_str("region"),
                access_key=get_str("access_key"),
                secret_key=get_str("secret_key"),
                session_token=get_str("session_token"),
                profile=get_str("profile"),
                role_arn=get_str("role_arn"),
                role_session_name=get_str("role_session_name"),
                external_id=get_str("external_id"),
                endpoint_url=get_str("endpoint_url"),
                connect_timeout=get_float("connect_timeout"),
                read_timeout=get_float("read_timeout"),
                max_retries=get_int("max_retries"),
                proxy_url=get_str("proxy_url"),
            )
        return self._s3_ops

    def _generate_key(self, model_instance: Any) -> str:
        """Generate S3 key for the file."""
        # Use model's primary key as part of the S3 key
        pk_value = ""
        if hasattr(model_instance, "_hash_key") and model_instance._hash_key:
            pk_value = str(getattr(model_instance, model_instance._hash_key, ""))
        if hasattr(model_instance, "_range_key") and model_instance._range_key:
            sk_value = str(getattr(model_instance, model_instance._range_key, ""))
            pk_value = f"{pk_value}/{sk_value}"

        # Clean up the key
        pk_value = pk_value.replace("#", "/").strip("/")

        return f"{self.prefix}{pk_value}"

    def serialize(self, value: S3File | S3Value | None) -> dict[str, Any] | None:
        """Serialize S3 value to DynamoDB format.

        Note: Actual upload happens in Model.save() via upload_to_s3().
        This just returns the metadata dict.
        """
        if value is None:
            return None

        if isinstance(value, S3Value):
            # Already uploaded, return metadata
            result: dict[str, Any] = {
                "bucket": value.bucket,
                "key": value.key,
                "size": value.size,
                "etag": value.etag,
            }
            if value.content_type:
                result["content_type"] = value.content_type
            if value.last_modified:
                result["last_modified"] = value.last_modified
            if value.version_id:
                result["version_id"] = value.version_id
            if value.metadata:
                result["metadata"] = value.metadata
            return result

        if isinstance(value, S3File):
            # S3File should be uploaded before serialization
            # This is handled by Model.save()
            raise ValueError(
                "S3File must be uploaded before serialization. "
                "This should be handled by Model.save()."
            )

        raise TypeError(f"Expected S3File or S3Value, got {type(value)}")

    def deserialize(self, value: dict[str, Any] | None) -> S3Value | None:
        """Deserialize DynamoDB value to S3Value."""
        if value is None:
            return None

        # Create S3Value from metadata
        # Note: s3_ops will be set when accessed via model
        return S3Value(
            bucket=value["bucket"],
            key=value["key"],
            size=value["size"],
            etag=value["etag"],
            content_type=value.get("content_type"),
            s3_ops=self._s3_ops,  # type: ignore[arg-type]
            last_modified=value.get("last_modified"),
            version_id=value.get("version_id"),
            metadata=value.get("metadata"),
        )

    def upload_to_s3(
        self,
        value: S3File,
        model_instance: Any,
        client: DynamoDBClient,
    ) -> S3Value:
        """Upload S3File to S3 and return S3Value.

        Called by Model.save() before serialization.
        """
        s3_ops = self._get_s3_ops(client)
        key = f"{self._generate_key(model_instance)}/{value.name}"

        metadata = s3_ops.upload_bytes(
            self.bucket,
            key,
            value.data,
            value.content_type,
            value.metadata,
        )

        return S3Value(
            bucket=metadata.bucket,
            key=metadata.key,
            size=metadata.size,
            etag=metadata.etag,
            content_type=metadata.content_type,
            s3_ops=s3_ops,
            last_modified=metadata.last_modified,
            version_id=metadata.version_id,
            metadata=metadata.metadata,
        )

    async def async_upload_to_s3(
        self,
        value: S3File,
        model_instance: Any,
        client: DynamoDBClient,
    ) -> S3Value:
        """Async upload S3File to S3."""
        s3_ops = self._get_s3_ops(client)
        key = f"{self._generate_key(model_instance)}/{value.name}"

        metadata = await s3_ops.async_upload_bytes(
            self.bucket,
            key,
            value.data,
            value.content_type,
            value.metadata,
        )

        return S3Value(
            bucket=metadata.bucket,
            key=metadata.key,
            size=metadata.size,
            etag=metadata.etag,
            content_type=metadata.content_type,
            s3_ops=s3_ops,
            last_modified=metadata.last_modified,
            version_id=metadata.version_id,
            metadata=metadata.metadata,
        )

    def delete_from_s3(self, value: S3Value, client: DynamoDBClient) -> None:
        """Delete file from S3.

        Called by Model.delete().
        """
        s3_ops = self._get_s3_ops(client)
        s3_ops.delete_object(value.bucket, value.key)

    async def async_delete_from_s3(self, value: S3Value, client: DynamoDBClient) -> None:
        """Async delete file from S3."""
        s3_ops = self._get_s3_ops(client)
        await s3_ops.async_delete_object(value.bucket, value.key)
