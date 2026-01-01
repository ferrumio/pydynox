"""Type stubs for pydynox_core (Rust module)."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

# Metrics
class OperationMetrics:
    duration_ms: float
    consumed_rcu: float | None
    consumed_wcu: float | None
    request_id: str | None
    items_count: int | None
    scanned_count: int | None

    def __init__(self, duration_ms: float = 0.0) -> None: ...

# Client
class DynamoDBClient:
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
    ) -> OperationMetrics: ...
    def get_item(
        self,
        table: str,
        key: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, OperationMetrics]: ...
    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics: ...
    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics: ...
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
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, OperationMetrics]: ...
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
        global_secondary_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
    ) -> None: ...
    def table_exists(self, table_name: str) -> bool: ...
    def delete_table(self, table_name: str) -> None: ...
    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None: ...

    # Async methods
    def async_get_item(
        self,
        table: str,
        key: dict[str, Any],
    ) -> Coroutine[Any, Any, dict[str, Any]]: ...
    def async_put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> Coroutine[Any, Any, OperationMetrics]: ...
    def async_delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> Coroutine[Any, Any, OperationMetrics]: ...
    def async_update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> Coroutine[Any, Any, OperationMetrics]: ...
    def async_query_page(
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
    ) -> Coroutine[Any, Any, dict[str, Any]]: ...

# Rate limiting
class FixedRate:
    def __init__(
        self,
        rcu: int | None = None,
        wcu: int | None = None,
        burst: int | None = None,
    ) -> None: ...
    def _acquire_rcu(self, rcu: float) -> None: ...
    def _acquire_wcu(self, wcu: float) -> None: ...
    def _on_throttle(self) -> None: ...

class AdaptiveRate:
    def __init__(
        self,
        max_rcu: int,
        max_wcu: int | None = None,
        min_rcu: int = 1,
        min_wcu: int = 1,
    ) -> None: ...
    def _acquire_rcu(self, rcu: float) -> None: ...
    def _acquire_wcu(self, wcu: float) -> None: ...
    def _on_throttle(self) -> None: ...

class RateLimitMetrics:
    rcu_acquired: float
    wcu_acquired: float
    throttle_count: int

# Tracing
def enable_sdk_debug() -> None: ...

# Serialization
def py_to_dynamo(value: Any) -> dict[str, Any]: ...
def dynamo_to_py(value: dict[str, Any]) -> Any: ...
def item_to_dynamo(item: dict[str, Any]) -> dict[str, Any]: ...
def item_from_dynamo(item: dict[str, Any]) -> dict[str, Any]: ...

# Exceptions
class PydynoxError(Exception): ...
class TableNotFoundError(PydynoxError): ...
class TableAlreadyExistsError(PydynoxError): ...
class ValidationError(PydynoxError): ...
class ConditionCheckFailedError(PydynoxError): ...
class TransactionCanceledError(PydynoxError): ...
class ThrottlingError(PydynoxError): ...
class AccessDeniedError(PydynoxError): ...
class CredentialsError(PydynoxError): ...
class SerializationError(PydynoxError): ...
class ConnectionError(PydynoxError): ...
class EncryptionError(PydynoxError): ...

# Compression
class CompressionAlgorithm:
    Zstd: CompressionAlgorithm
    Lz4: CompressionAlgorithm
    Gzip: CompressionAlgorithm

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

# Encryption
class KmsEncryptor:
    key_id: str

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
