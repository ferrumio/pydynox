"""Base client with initialization and rate limiting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydynox import pydynox_core
    from pydynox._internal._metrics import ModelMetrics, OperationMetrics
    from pydynox.diagnostics import HotPartitionDetector
    from pydynox.rate_limit import AdaptiveRate, FixedRate


class BaseClient:
    """Base client with rate limiting support."""

    _client: pydynox_core.DynamoDBClient
    _rate_limit: FixedRate | AdaptiveRate | None
    _diagnostics: HotPartitionDetector | None
    _config: dict[str, str | float | int | None]
    _last_metrics: OperationMetrics | None
    _total_metrics: ModelMetrics

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
        rate_limit: FixedRate | AdaptiveRate | None = None,
        diagnostics: HotPartitionDetector | None = None,
    ):
        from pydynox import pydynox_core
        from pydynox._internal._metrics import ModelMetrics

        self._client = pydynox_core.DynamoDBClient(
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            profile=profile,
            endpoint_url=endpoint_url,
            role_arn=role_arn,
            role_session_name=role_session_name,
            external_id=external_id,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            max_retries=max_retries,
            proxy_url=proxy_url,
        )
        self._rate_limit = rate_limit
        self._diagnostics = diagnostics
        self._last_metrics = None
        self._total_metrics = ModelMetrics()

        # Store config for S3/KMS to inherit
        self._config = {
            "region": region,
            "access_key": access_key,
            "secret_key": secret_key,
            "session_token": session_token,
            "profile": profile,
            "endpoint_url": endpoint_url,
            "role_arn": role_arn,
            "role_session_name": role_session_name,
            "external_id": external_id,
            "connect_timeout": connect_timeout,
            "read_timeout": read_timeout,
            "max_retries": max_retries,
            "proxy_url": proxy_url,
        }

    @property
    def rate_limit(self) -> FixedRate | AdaptiveRate | None:
        """Get the rate limiter for this client."""
        return self._rate_limit

    @property
    def diagnostics(self) -> HotPartitionDetector | None:
        """Get the diagnostics detector for this client."""
        return self._diagnostics

    def _acquire_rcu(self, rcu: float = 1.0) -> None:
        """Acquire read capacity before an operation."""
        if self._rate_limit is not None:
            self._rate_limit._acquire_rcu(rcu)

    def _acquire_wcu(self, wcu: float = 1.0) -> None:
        """Acquire write capacity before an operation."""
        if self._rate_limit is not None:
            self._rate_limit._acquire_wcu(wcu)

    def _on_throttle(self) -> None:
        """Record a throttle event."""
        if self._rate_limit is not None:
            self._rate_limit._on_throttle()

    def _record_write(self, table: str, pk: str) -> None:
        """Record a write for hot partition detection."""
        if self._diagnostics is not None:
            self._diagnostics.record_write(table, pk)

    def _record_read(self, table: str, pk: str) -> None:
        """Record a read for hot partition detection."""
        if self._diagnostics is not None:
            self._diagnostics.record_read(table, pk)

    def get_region(self) -> str:
        """Get the configured AWS region."""
        return self._client.get_region()

    def get_last_metrics(self) -> OperationMetrics | None:
        """Get metrics from the last operation.

        Returns the OperationMetrics from the most recent operation,
        or None if no operations have been performed.

        Example:
            client.get_item("users", {"pk": "USER#1"})
            metrics = client.get_last_metrics()
            print(metrics.duration_ms)
        """
        return self._last_metrics

    def get_total_metrics(self) -> ModelMetrics:
        """Get aggregated metrics from all operations.

        Returns total RCU/WCU consumed and operation counts
        since the client was created or last reset.

        Example:
            client.get_item("users", {"pk": "USER#1"})
            client.put_item("users", {"pk": "USER#2", "name": "John"})
            total = client.get_total_metrics()
            print(total.total_rcu)  # Total RCU consumed
            print(total.operation_count)  # 2
        """
        return self._total_metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to zero.

        Useful in long-running processes to reset metrics
        at the start of each request.

        Example:
            def handle_request():
                client.reset_metrics()
                # ... do operations ...
                print(client.get_total_metrics().total_rcu)
        """
        self._last_metrics = None
        self._total_metrics.reset()

    def ping(self) -> bool:
        """Check if the client can connect to DynamoDB."""
        return self._client.ping()

    def _get_client_config(self) -> dict[str, str | float | int | None]:
        """Get client config for S3/KMS to inherit credentials.

        Internal method used by S3Attribute and EncryptedAttribute.
        """
        return self._config
