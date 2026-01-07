"""Diagnostics tools for DynamoDB access patterns."""

from pydynox.diagnostics.hot_partition import HotPartitionDetector

__all__ = ["HotPartitionDetector"]
