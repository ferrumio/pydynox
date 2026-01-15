"""S3 file upload/delete helpers for S3Attribute."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydynox._internal._operations_metrics import _record_s3_metrics
from pydynox._internal._s3 import S3File, S3Value
from pydynox.attributes.s3 import S3Attribute

if TYPE_CHECKING:
    from pydynox.model import Model


def _upload_s3_files(self: Model) -> None:
    """Upload S3File values to S3 and replace with S3Value."""
    client = self._get_client()
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, S3Attribute):
            value = getattr(self, attr_name, None)
            if isinstance(value, S3File):
                s3_value, metrics = attr.upload_to_s3(value, self, client)
                setattr(self, attr_name, s3_value)
                # Record S3 metrics
                _record_s3_metrics(
                    metrics.duration_ms,
                    metrics.calls,
                    metrics.bytes_uploaded,
                    metrics.bytes_downloaded,
                )


async def _async_upload_s3_files(self: Model) -> None:
    """Async upload S3File values to S3 and replace with S3Value."""
    client = self._get_client()
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, S3Attribute):
            value = getattr(self, attr_name, None)
            if isinstance(value, S3File):
                s3_value, metrics = await attr.async_upload_to_s3(value, self, client)
                setattr(self, attr_name, s3_value)
                # Record S3 metrics
                _record_s3_metrics(
                    metrics.duration_ms,
                    metrics.calls,
                    metrics.bytes_uploaded,
                    metrics.bytes_downloaded,
                )


def _delete_s3_files(self: Model) -> None:
    """Delete S3 files associated with this model."""
    client = self._get_client()
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, S3Attribute):
            value = getattr(self, attr_name, None)
            if isinstance(value, S3Value):
                metrics = attr.delete_from_s3(value, client)
                # Record S3 metrics
                _record_s3_metrics(
                    metrics.duration_ms,
                    metrics.calls,
                    metrics.bytes_uploaded,
                    metrics.bytes_downloaded,
                )


async def _async_delete_s3_files(self: Model) -> None:
    """Async delete S3 files associated with this model."""
    client = self._get_client()
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, S3Attribute):
            value = getattr(self, attr_name, None)
            if isinstance(value, S3Value):
                metrics = await attr.async_delete_from_s3(value, client)
                # Record S3 metrics
                _record_s3_metrics(
                    metrics.duration_ms,
                    metrics.calls,
                    metrics.bytes_uploaded,
                    metrics.bytes_downloaded,
                )
