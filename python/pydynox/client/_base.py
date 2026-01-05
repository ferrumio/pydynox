"""Base client with initialization and rate limiting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydynox import pydynox_core
    from pydynox.rate_limit import AdaptiveRate, FixedRate


class BaseClient:
    """Base client with rate limiting support."""

    _client: pydynox_core.DynamoDBClient
    _rate_limit: FixedRate | AdaptiveRate | None

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
    ):
        from pydynox import pydynox_core

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

    @property
    def rate_limit(self) -> FixedRate | AdaptiveRate | None:
        """Get the rate limiter for this client."""
        return self._rate_limit

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

    def get_region(self) -> str:
        """Get the configured AWS region."""
        return self._client.get_region()

    def ping(self) -> bool:
        """Check if the client can connect to DynamoDB."""
        return self._client.ping()
