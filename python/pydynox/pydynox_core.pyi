"""Type stubs for pydynox_core (Rust module)."""

from __future__ import annotations

from collections.abc import Awaitable
from decimal import Decimal
from typing import Any, TypedDict, overload

from pydynox._internal._decimal import NumberSchema

# Metrics
class OperationMetrics:
    duration_ms: float
    consumed_rcu: float | None
    consumed_wcu: float | None
    request_id: str | None
    items_count: int | None
    scanned_count: int | None
    vector_search_bytes: float | None
    vector_write_bytes: float | None

    def __init__(self, duration_ms: float = 0.0) -> None: ...

# Results resolved by DynamoDBClient awaitables (plain dicts at runtime)
class _GetItemResult(TypedDict):
    item: dict[str, Any] | None
    metrics: OperationMetrics

class _PageResult(TypedDict):
    items: list[dict[str, Any]]
    last_evaluated_key: dict[str, Any] | None
    metrics: OperationMetrics

class _CountResult(TypedDict):
    count: int
    metrics: OperationMetrics

class _ParallelScanResult(TypedDict):
    items: list[dict[str, Any]]
    metrics: OperationMetrics

class _StatementResult(TypedDict):
    items: list[dict[str, Any]]
    next_token: str | None
    metrics: OperationMetrics

class _VectorMatch(TypedDict):
    item: dict[str, Any]
    score: float

class _VectorSearchResult(TypedDict):
    matches: list[_VectorMatch]
    metrics: OperationMetrics

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
        role_arn: str | None = None,
        role_session_name: str | None = None,
        external_id: str | None = None,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
        max_retries: int | None = None,
        proxy_url: str | None = None,
    ) -> None: ...
    def get_region(self) -> str: ...
    def ping(self) -> bool: ...

    # Basic operations. Async methods return awaitables; sync_ methods block.
    def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> Awaitable[tuple[dict[str, Any] | None, OperationMetrics]]: ...
    def sync_put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> tuple[dict[str, Any] | None, OperationMetrics]: ...
    def get_item(
        self,
        table: str,
        key: dict[str, Any],
        consistent_read: bool = False,
        projection: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_GetItemResult]: ...
    def sync_get_item(
        self,
        table: str,
        key: dict[str, Any],
        consistent_read: bool = False,
        projection: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> tuple[dict[str, Any] | None, OperationMetrics]: ...
    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> Awaitable[tuple[dict[str, Any] | None, OperationMetrics]]: ...
    def sync_delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> tuple[dict[str, Any] | None, OperationMetrics]: ...
    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> Awaitable[tuple[dict[str, Any] | None, OperationMetrics]]: ...
    def sync_update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
        return_values: str | None = None,
    ) -> tuple[dict[str, Any] | None, OperationMetrics]: ...

    # Query and scan
    def query_page(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_PageResult]: ...
    def sync_query_page(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, OperationMetrics]: ...
    def scan_page(
        self,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_PageResult]: ...
    def sync_scan_page(
        self,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, OperationMetrics]: ...
    def count(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
    ) -> Awaitable[_CountResult]: ...
    def sync_count(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
    ) -> tuple[int, OperationMetrics]: ...
    def parallel_scan(
        self,
        table: str,
        total_segments: int,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        consistent_read: bool = False,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_ParallelScanResult]: ...
    def sync_parallel_scan(
        self,
        table: str,
        total_segments: int,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        consistent_read: bool = False,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> tuple[list[dict[str, Any]], OperationMetrics]: ...

    # Batch operations
    def batch_write(
        self,
        table: str,
        put_items: list[dict[str, Any]],
        delete_keys: list[dict[str, Any]],
    ) -> Awaitable[None]: ...
    def sync_batch_write(
        self,
        table: str,
        put_items: list[dict[str, Any]],
        delete_keys: list[dict[str, Any]],
    ) -> None: ...
    def batch_get(
        self,
        table: str,
        keys: list[dict[str, Any]],
        consistent_read: bool,
        projection: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[list[dict[str, Any]]]: ...
    def sync_batch_get(
        self,
        table: str,
        keys: list[dict[str, Any]],
        consistent_read: bool,
        projection: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> list[dict[str, Any]]: ...

    # Transactions
    def transact_write(
        self,
        operations: list[dict[str, Any]],
        *,
        client_request_token: str | None = None,
    ) -> Awaitable[None]: ...
    def sync_transact_write(
        self,
        operations: list[dict[str, Any]],
        *,
        client_request_token: str | None = None,
    ) -> None: ...
    def transact_get(
        self, gets: list[dict[str, Any]]
    ) -> Awaitable[list[dict[str, Any] | None]]: ...
    def sync_transact_get(self, gets: list[dict[str, Any]]) -> list[dict[str, Any] | None]: ...

    # Table operations
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
        local_secondary_indexes: list[dict[str, Any]] | None = None,
        vector_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_create_table(
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
        local_secondary_indexes: list[dict[str, Any]] | None = None,
        vector_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None: ...
    def table_exists(self, table_name: str) -> Awaitable[bool]: ...
    def sync_table_exists(self, table_name: str) -> bool: ...
    def delete_table(
        self,
        table_name: str,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_delete_table(
        self,
        table_name: str,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None: ...
    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None: ...
    def wait_for_table_deleted(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_wait_for_table_deleted(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None: ...

    # Vector operations
    def search_vectors(
        self,
        table: str,
        index_name: str,
        vector: list[float],
        top_k: int = 10,
        search_condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        projection_expression: str | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_VectorSearchResult]: ...
    def sync_search_vectors(
        self,
        table: str,
        index_name: str,
        vector: list[float],
        top_k: int = 10,
        search_condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        projection_expression: str | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> _VectorSearchResult: ...
    def create_vector_index(
        self,
        table: str,
        definition: dict[str, Any],
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_create_vector_index(
        self,
        table: str,
        definition: dict[str, Any],
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None: ...
    def delete_vector_index(
        self,
        table: str,
        index_name: str,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> Awaitable[None]: ...
    def sync_delete_vector_index(
        self,
        table: str,
        index_name: str,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None: ...
    def describe_vector_index(
        self,
        table: str,
        index_name: str,
    ) -> Awaitable[dict[str, Any]]: ...
    def sync_describe_vector_index(
        self,
        table: str,
        index_name: str,
    ) -> dict[str, Any]: ...

    # PartiQL
    def execute_statement(
        self,
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
        next_token: str | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> Awaitable[_StatementResult]: ...
    def sync_execute_statement(
        self,
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
        next_token: str | None = None,
        *,
        _number_schema: NumberSchema | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, OperationMetrics]: ...

# Rate limiting
class FixedRate:
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

class RateLimitMetrics:
    @property
    def consumed_rcu(self) -> float: ...
    @property
    def consumed_wcu(self) -> float: ...
    @property
    def throttle_count(self) -> int: ...
    def reset(self) -> None: ...

# Tracing
def enable_sdk_debug() -> None: ...

# Serialization
def py_to_dynamo(value: Any) -> dict[str, Any]: ...
def dynamo_to_py(attr: dict[str, Any]) -> Any: ...
def item_to_dynamo(item: dict[str, Any]) -> dict[str, Any]: ...
def item_from_dynamo(
    item: dict[str, Any], *, _number_schema: NumberSchema | None = None
) -> dict[str, Any]: ...

# Exceptions
class PydynoxException(Exception): ...
class ResourceNotFoundException(PydynoxException): ...
class ResourceInUseException(PydynoxException): ...
class ValidationException(PydynoxException): ...

class ConditionalCheckFailedException(PydynoxException):
    # Set on the instance when the failed write asked for the existing item.
    item: dict[str, Any]

class TransactionCanceledException(PydynoxException): ...
class IdempotentParameterMismatchException(PydynoxException): ...
class ProvisionedThroughputExceededException(PydynoxException): ...
class AccessDeniedException(PydynoxException): ...
class CredentialsException(PydynoxException): ...
class SerializationException(PydynoxException): ...
class ConnectionException(PydynoxException): ...
class LockNotAcquired(PydynoxException): ...
class LockLost(PydynoxException): ...
class LockReleaseError(PydynoxException): ...
class EncryptionException(PydynoxException): ...
class S3Exception(PydynoxException): ...
class S3AttributeException(S3Exception): ...

# Distributed locks (internal bindings)
class LockMetrics:
    @property
    def read_requests(self) -> int: ...
    @property
    def write_requests(self) -> int: ...
    @property
    def conditional_failures(self) -> int: ...
    @property
    def request_failures(self) -> int: ...
    @property
    def wait_timeouts(self) -> int: ...
    @property
    def cleanup_failures(self) -> int: ...
    @property
    def consumed_rcu(self) -> float: ...
    @property
    def consumed_wcu(self) -> float: ...
    @property
    def renewals(self) -> int: ...
    @property
    def wait_ms(self) -> float: ...
    @property
    def lost(self) -> bool: ...

class MemoryLockState:
    def __init__(self) -> None: ...

class NativeLease:
    def __init__(
        self,
        backend: Any,
        table: str,
        key: str,
        lease_duration: float = 30.0,
        wait_timeout: float = 35.0,
    ) -> None: ...
    def acquire(self) -> Awaitable[None]: ...
    def sync_acquire(self) -> None: ...
    def release(self) -> Awaitable[None]: ...
    def sync_release(self) -> None: ...
    def cancel(self) -> None: ...
    def raise_if_lost(self) -> None: ...
    def condition_check(self) -> dict[str, Any]: ...
    @property
    def metrics(self) -> LockMetrics: ...

class LockKeyTemplate:
    def __init__(
        self,
        template: str,
        parameters: list[tuple[str, int, bool, Any]],
        lease_duration: float,
        wait_timeout: float,
    ) -> None: ...
    def resolve(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str: ...

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

# Encryption (uses envelope encryption with GenerateDataKey + local AES-256-GCM)
class KmsMetrics:
    duration_ms: float
    kms_calls: int

    def __init__(self, duration_ms: float = 0.0, kms_calls: int = 0) -> None: ...

class EncryptResult:
    ciphertext: str
    metrics: KmsMetrics

class DecryptResult:
    plaintext: str
    metrics: KmsMetrics

class KmsEncryptor:
    key_id: str

    def __init__(
        self,
        key_id: str,
        region: str | None = None,
        context: dict[str, str] | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        profile: str | None = None,
        role_arn: str | None = None,
        role_session_name: str | None = None,
        external_id: str | None = None,
        endpoint_url: str | None = None,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
        max_retries: int | None = None,
        proxy_url: str | None = None,
    ) -> None: ...
    # Sync methods (blocking)
    def sync_encrypt(self, plaintext: str) -> str: ...
    def sync_decrypt(self, ciphertext: str) -> str: ...
    def sync_encrypt_with_metrics(self, plaintext: str) -> EncryptResult: ...
    def sync_decrypt_with_metrics(self, ciphertext: str) -> DecryptResult: ...
    # Async methods (default)
    def encrypt(self, plaintext: str) -> Awaitable[str]: ...
    def decrypt(self, ciphertext: str) -> Awaitable[str]: ...
    def encrypt_with_metrics(self, plaintext: str) -> Awaitable[EncryptResult]: ...
    def decrypt_with_metrics(self, ciphertext: str) -> Awaitable[DecryptResult]: ...
    @staticmethod
    def is_encrypted(value: str) -> bool: ...

# Generators
def generate_uuid4() -> str: ...
def generate_ulid() -> str: ...
def generate_ksuid() -> str: ...
def generate_epoch() -> int: ...
def generate_epoch_ms() -> int: ...
def generate_iso8601() -> str: ...

# S3
class S3Metadata:
    bucket: str
    key: str
    size: int
    etag: str
    content_type: str | None
    last_modified: str | None
    version_id: str | None
    metadata: dict[str, str] | None

    def to_dict(self) -> dict[str, Any]: ...

class S3Metrics:
    duration_ms: float
    calls: int
    bytes_uploaded: int
    bytes_downloaded: int

    def __init__(
        self,
        duration_ms: float = 0.0,
        calls: int = 0,
        bytes_uploaded: int = 0,
        bytes_downloaded: int = 0,
    ) -> None: ...

class S3Operations:
    def __init__(
        self,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        profile: str | None = None,
        role_arn: str | None = None,
        role_session_name: str | None = None,
        external_id: str | None = None,
        endpoint_url: str | None = None,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
        max_retries: int | None = None,
        proxy_url: str | None = None,
    ) -> None: ...

    # Async methods (default, no prefix) - return Coroutines
    def upload_bytes(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Awaitable[tuple[S3Metadata, S3Metrics]]: ...
    def download_bytes(self, bucket: str, key: str) -> Awaitable[tuple[bytes, S3Metrics]]: ...
    def presigned_url(
        self, bucket: str, key: str, expires_secs: int = 3600
    ) -> Awaitable[tuple[str, S3Metrics]]: ...
    def delete_object(self, bucket: str, key: str) -> Awaitable[S3Metrics]: ...
    def head_object(self, bucket: str, key: str) -> Awaitable[tuple[S3Metadata, S3Metrics]]: ...
    def save_to_file(
        self, bucket: str, key: str, path: str
    ) -> Awaitable[tuple[int, S3Metrics]]: ...

    # Sync methods (with sync_ prefix) - return tuples with metrics
    def sync_upload_bytes(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> tuple[S3Metadata, S3Metrics]: ...
    def sync_download_bytes(self, bucket: str, key: str) -> tuple[bytes, S3Metrics]: ...
    def sync_presigned_url(
        self, bucket: str, key: str, expires_secs: int = 3600
    ) -> tuple[str, S3Metrics]: ...
    def sync_delete_object(self, bucket: str, key: str) -> S3Metrics: ...
    def sync_head_object(self, bucket: str, key: str) -> tuple[S3Metadata, S3Metrics]: ...
    def sync_save_to_file(self, bucket: str, key: str, path: str) -> tuple[int, S3Metrics]: ...

# Diagnostics
class HotPartitionTracker:
    def __init__(
        self,
        writes_threshold: int,
        reads_threshold: int,
        window_seconds: int,
    ) -> None: ...
    def record_write(self, table: str, pk: str) -> str | None: ...
    def record_read(self, table: str, pk: str) -> str | None: ...
    def get_write_count(self, table: str, pk: str) -> int: ...
    def get_read_count(self, table: str, pk: str) -> int: ...
    def clear(self) -> None: ...

@overload
def validate_decimal(value: Decimal | int) -> Decimal: ...
@overload
def validate_decimal(value: None) -> None: ...
@overload
def validate_decimal(value: object) -> Decimal | None: ...
def decimal_to_number(value: Decimal) -> int | float: ...
