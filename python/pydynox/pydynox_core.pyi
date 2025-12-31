"""Type stubs for pydynox_core Rust module.

This file provides type hints for the Rust-implemented pydynox_core module.
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# DynamoDB Client
# =============================================================================

class DynamoDBClient:
    """DynamoDB client with flexible credential configuration."""

    def __init__(
        self,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        profile: str | None = None,
        endpoint_url: str | None = None,
    ) -> None: ...
    def get_region(self) -> str: ...
    def ping(self) -> bool: ...
    def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None: ...
    def get_item(self, table: str, key: dict[str, Any]) -> dict[str, Any] | None: ...
    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None: ...
    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None: ...
    def query_page(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]: ...
    def batch_write(
        self,
        table: str,
        put_items: list[dict[str, Any]],
        delete_keys: list[dict[str, Any]],
    ) -> None: ...
    def batch_get(
        self,
        table: str,
        keys: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...
    def transact_write(self, operations: list[dict[str, Any]]) -> None: ...
    def create_table(
        self,
        table_name: str,
        hash_key: tuple[str, str],
        range_key: tuple[str, str] | None = None,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        wait: bool = False,
    ) -> None: ...
    def table_exists(self, table_name: str) -> bool: ...
    def delete_table(self, table_name: str) -> None: ...
    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None: ...

# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimitMetrics:
    """Metrics for monitoring rate limiter behavior."""

    @property
    def consumed_rcu(self) -> float: ...
    @property
    def consumed_wcu(self) -> float: ...
    @property
    def throttle_count(self) -> int: ...
    def reset(self) -> None: ...

class FixedRate:
    """Fixed rate limiter."""

    def __init__(
        self,
        rcu: float | None = None,
        wcu: float | None = None,
        burst: float | None = None,
    ) -> None: ...
    @property
    def rcu(self) -> float | None: ...
    @property
    def wcu(self) -> float | None: ...
    @property
    def metrics(self) -> RateLimitMetrics: ...
    @property
    def consumed_rcu(self) -> float: ...
    @property
    def consumed_wcu(self) -> float: ...
    @property
    def throttle_count(self) -> int: ...
    def _acquire_rcu(self, rcu: float) -> None: ...
    def _acquire_wcu(self, wcu: float) -> None: ...
    def _on_throttle(self) -> None: ...

class AdaptiveRate:
    """Adaptive rate limiter that adjusts based on throttling."""

    def __init__(
        self,
        max_rcu: float,
        max_wcu: float | None = None,
        min_rcu: float | None = None,
        min_wcu: float | None = None,
    ) -> None: ...
    @property
    def current_rcu(self) -> float: ...
    @property
    def current_wcu(self) -> float | None: ...
    @property
    def max_rcu(self) -> float: ...
    @property
    def max_wcu(self) -> float | None: ...
    @property
    def consumed_rcu(self) -> float: ...
    @property
    def consumed_wcu(self) -> float: ...
    @property
    def throttle_count(self) -> int: ...
    def _acquire_rcu(self, rcu: float) -> None: ...
    def _acquire_wcu(self, wcu: float) -> None: ...
    def _on_throttle(self) -> None: ...

# =============================================================================
# Compression
# =============================================================================

class CompressionAlgorithm:
    """Compression algorithm options."""

    Zstd: int
    Lz4: int
    Gzip: int

def compress(
    data: bytes,
    algorithm: CompressionAlgorithm | None = None,
    level: int | None = None,
) -> bytes: ...
def decompress(
    data: bytes,
    algorithm: CompressionAlgorithm | None = None,
) -> bytes: ...
def should_compress(
    data: bytes,
    algorithm: CompressionAlgorithm | None = None,
    threshold: float | None = None,
) -> bool: ...
def compress_string(
    value: str,
    algorithm: CompressionAlgorithm | None = None,
    level: int | None = None,
    min_size: int | None = None,
    threshold: float | None = None,
) -> str: ...
def decompress_string(value: str) -> str: ...

# =============================================================================
# Encryption
# =============================================================================

class KmsEncryptor:
    """KMS encryptor for field-level encryption."""

    def __init__(
        self,
        key_id: str,
        region: str | None = None,
        context: dict[str, str] | None = None,
    ) -> None: ...
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...
    @staticmethod
    def is_encrypted(value: str) -> bool: ...
    @property
    def key_id(self) -> str: ...

# =============================================================================
# Serialization
# =============================================================================

def py_to_dynamo_py(value: Any) -> dict[str, Any]: ...
def dynamo_to_py_py(value: dict[str, Any]) -> Any: ...
def item_to_dynamo(item: dict[str, Any]) -> dict[str, dict[str, Any]]: ...
def item_from_dynamo(item: dict[str, dict[str, Any]]) -> dict[str, Any]: ...

# =============================================================================
# Exceptions
# =============================================================================

class PydynoxError(Exception):
    """Base exception for all pydynox errors."""

    ...

class TableNotFoundError(PydynoxError):
    """Table does not exist."""

    ...

class TableAlreadyExistsError(PydynoxError):
    """Table already exists."""

    ...

class ValidationError(PydynoxError):
    """Invalid request."""

    ...

class ConditionCheckFailedError(PydynoxError):
    """Condition expression failed."""

    ...

class TransactionCanceledError(PydynoxError):
    """Transaction was canceled."""

    ...

class ThrottlingError(PydynoxError):
    """Rate limit exceeded."""

    ...

class AccessDeniedError(PydynoxError):
    """IAM permission denied."""

    ...

class CredentialsError(PydynoxError):
    """AWS credentials issue."""

    ...

class SerializationError(PydynoxError):
    """Data conversion error."""

    ...

class ConnectionError(PydynoxError):
    """Network/endpoint issue."""

    ...

class EncryptionError(PydynoxError):
    """KMS/encryption error."""

    ...
