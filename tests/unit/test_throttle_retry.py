"""Tests for adaptive retry on throttling."""

import pytest
from pydynox._internal import _throttle_retry
from pydynox._internal._throttle_retry import (
    _MAX_ATTEMPTS,
    _backoff_for,
    retry_on_throttle,
    sync_retry_on_throttle,
)
from pydynox.exceptions import ProvisionedThroughputExceededException
from pydynox.rate_limit import AdaptiveRate


class FakeClient:
    """Minimal stand-in for a client with a rate limiter."""

    def __init__(self, rate_limit=None, fail_times=0):
        self._rate_limit = rate_limit
        self._fail_times = fail_times
        self.calls = 0
        self.throttles = 0

    def _on_throttle(self):
        self.throttles += 1
        if self._rate_limit is not None:
            self._rate_limit._on_throttle()

    @sync_retry_on_throttle
    def sync_op(self):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise ProvisionedThroughputExceededException("throttled")
        return "ok"

    @retry_on_throttle
    async def async_op(self):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise ProvisionedThroughputExceededException("throttled")
        return "ok"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Skip the real backoff waits so tests stay fast."""
    monkeypatch.setattr(_throttle_retry.time, "sleep", lambda _: None)

    async def fake_async_sleep(_):
        return None

    monkeypatch.setattr(_throttle_retry.asyncio, "sleep", fake_async_sleep)


def test_sync_retries_until_success():
    # GIVEN a client with a limiter whose first two calls are throttled
    client = FakeClient(rate_limit=AdaptiveRate(max_rcu=100), fail_times=2)

    # WHEN we run the operation
    result = client.sync_op()

    # THEN it retried and eventually succeeded
    assert result == "ok"
    assert client.calls == 3


def test_sync_lowers_rate_before_retrying():
    # GIVEN an adaptive limiter starting at half of max
    limiter = AdaptiveRate(max_rcu=100)
    assert limiter.current_rcu == 50.0
    client = FakeClient(rate_limit=limiter, fail_times=2)

    # WHEN two attempts are throttled
    client.sync_op()

    # THEN the rate dropped 20% per throttle (50 -> 40 -> 32)
    assert limiter.current_rcu == 32.0
    assert limiter.throttle_count == 2


def test_sync_without_rate_limit_fails_fast():
    # GIVEN a client with no rate limiter
    client = FakeClient(rate_limit=None, fail_times=1)

    # WHEN the operation is throttled
    with pytest.raises(ProvisionedThroughputExceededException):
        client.sync_op()

    # THEN it was tried once, with no throttle feedback
    assert client.calls == 1
    assert client.throttles == 0


def test_sync_gives_up_after_max_attempts():
    # GIVEN a client that is always throttled
    client = FakeClient(rate_limit=AdaptiveRate(max_rcu=100), fail_times=999)

    # WHEN we run the operation
    with pytest.raises(ProvisionedThroughputExceededException):
        client.sync_op()

    # THEN it stopped at the attempt limit and reported every throttle
    assert client.calls == _MAX_ATTEMPTS
    assert client.throttles == _MAX_ATTEMPTS


def test_sync_passes_through_when_not_throttled():
    # GIVEN a client that never fails
    client = FakeClient(rate_limit=AdaptiveRate(max_rcu=100))

    # WHEN we run the operation
    result = client.sync_op()

    # THEN it ran once with no retries
    assert result == "ok"
    assert client.calls == 1
    assert client.throttles == 0


@pytest.mark.asyncio
async def test_async_retries_until_success():
    # GIVEN a client with a limiter whose first two calls are throttled
    client = FakeClient(rate_limit=AdaptiveRate(max_rcu=100), fail_times=2)

    # WHEN we await the operation
    result = await client.async_op()

    # THEN it retried and eventually succeeded
    assert result == "ok"
    assert client.calls == 3


@pytest.mark.asyncio
async def test_async_without_rate_limit_fails_fast():
    # GIVEN a client with no rate limiter
    client = FakeClient(rate_limit=None, fail_times=1)

    # WHEN the operation is throttled
    with pytest.raises(ProvisionedThroughputExceededException):
        await client.async_op()

    # THEN it was tried once
    assert client.calls == 1
    assert client.throttles == 0


@pytest.mark.asyncio
async def test_async_gives_up_after_max_attempts():
    # GIVEN a client that is always throttled
    client = FakeClient(rate_limit=AdaptiveRate(max_rcu=100), fail_times=999)

    # WHEN we await the operation
    with pytest.raises(ProvisionedThroughputExceededException):
        await client.async_op()

    # THEN it stopped at the attempt limit
    assert client.calls == _MAX_ATTEMPTS


def test_backoff_doubles_then_caps():
    # GIVEN the documented backoff schedule
    # WHEN we compute the first attempts
    # THEN it doubles from 0.1s
    assert _backoff_for(0) == 0.1
    assert _backoff_for(1) == 0.2
    assert _backoff_for(2) == 0.4

    # AND it never exceeds the 5s cap
    assert _backoff_for(20) == 5.0


def test_other_errors_are_not_retried():
    # GIVEN a client whose operation raises an unrelated error
    class Boom(FakeClient):
        @sync_retry_on_throttle
        def sync_op(self):
            self.calls += 1
            raise ValueError("not a throttle")

    client = Boom(rate_limit=AdaptiveRate(max_rcu=100))

    # WHEN we run it
    with pytest.raises(ValueError):
        client.sync_op()

    # THEN it was not retried
    assert client.calls == 1
