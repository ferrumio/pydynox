"""Tests for rate limiting."""

import time

import pytest


def test_fixed_rate_creation():
    """Test creating a FixedRate limiter."""
    from pydynox.rate_limit import FixedRate

    limiter = FixedRate(rcu=50)
    assert limiter.rcu == 50
    assert limiter.wcu is None


def test_fixed_rate_with_wcu():
    """Test FixedRate with both RCU and WCU."""
    from pydynox.rate_limit import FixedRate

    limiter = FixedRate(rcu=50, wcu=25)
    assert limiter.rcu == 50
    assert limiter.wcu == 25


def test_fixed_rate_metrics():
    """Test FixedRate metrics tracking."""
    from pydynox.rate_limit import FixedRate

    limiter = FixedRate(rcu=100, wcu=50)

    # Initial metrics should be zero
    assert limiter.consumed_rcu == 0
    assert limiter.consumed_wcu == 0
    assert limiter.throttle_count == 0

    # Acquire some capacity
    limiter._acquire_rcu(10.0)
    limiter._acquire_wcu(5.0)

    assert limiter.consumed_rcu == 10.0
    assert limiter.consumed_wcu == 5.0


def test_adaptive_rate_creation():
    """Test creating an AdaptiveRate limiter."""
    from pydynox.rate_limit import AdaptiveRate

    limiter = AdaptiveRate(max_rcu=100)

    # Should start at 50% of max
    assert limiter.current_rcu == 50.0
    assert limiter.max_rcu == 100.0


def test_adaptive_rate_with_wcu():
    """Test AdaptiveRate with both RCU and WCU."""
    from pydynox.rate_limit import AdaptiveRate

    limiter = AdaptiveRate(max_rcu=100, max_wcu=50)

    assert limiter.current_rcu == 50.0
    assert limiter.current_wcu == 25.0
    assert limiter.max_rcu == 100.0
    assert limiter.max_wcu == 50.0


def test_adaptive_rate_throttle_reduces_rate():
    """Test that throttle events reduce the rate."""
    from pydynox.rate_limit import AdaptiveRate

    limiter = AdaptiveRate(max_rcu=100)

    # Initial rate is 50
    assert limiter.current_rcu == 50.0

    # After throttle, should be 40 (50 * 0.8)
    limiter._on_throttle()
    assert limiter.current_rcu == 40.0

    # After another throttle, should be 32 (40 * 0.8)
    limiter._on_throttle()
    assert limiter.current_rcu == 32.0

    # Throttle count should be 2
    assert limiter.throttle_count == 2


def test_adaptive_rate_min_rcu():
    """Test that rate doesn't go below min_rcu."""
    from pydynox.rate_limit import AdaptiveRate

    limiter = AdaptiveRate(max_rcu=100, min_rcu=10)

    # Throttle many times
    for _ in range(20):
        limiter._on_throttle()

    # Should not go below min
    assert limiter.current_rcu >= 10.0


def test_fixed_rate_rate_limiting():
    """Test that FixedRate actually limits the rate."""
    from pydynox.rate_limit import FixedRate

    # Very low rate to make test fast
    limiter = FixedRate(rcu=10)

    # Acquire all tokens
    start = time.time()
    limiter._acquire_rcu(10.0)
    first_acquire = time.time() - start

    # First acquire should be instant (tokens available)
    assert first_acquire < 0.1

    # Second acquire should wait for refill
    start = time.time()
    limiter._acquire_rcu(5.0)
    second_acquire = time.time() - start

    # Should have waited ~0.5 seconds for 5 tokens at 10/sec
    assert second_acquire >= 0.4


@pytest.mark.parametrize(
    "rcu,wcu,burst",
    [
        pytest.param(50, None, None, id="rcu_only"),
        pytest.param(50, 25, None, id="rcu_and_wcu"),
        pytest.param(50, 25, 100, id="with_burst"),
    ],
)
def test_fixed_rate_configurations(rcu, wcu, burst):
    """Test various FixedRate configurations."""
    from pydynox.rate_limit import FixedRate

    limiter = FixedRate(rcu=rcu, wcu=wcu, burst=burst)
    assert limiter.rcu == rcu
    assert limiter.wcu == wcu


@pytest.mark.parametrize(
    "max_rcu,max_wcu,min_rcu",
    [
        pytest.param(100, None, None, id="rcu_only"),
        pytest.param(100, 50, None, id="rcu_and_wcu"),
        pytest.param(100, 50, 10, id="with_min"),
    ],
)
def test_adaptive_rate_configurations(max_rcu, max_wcu, min_rcu):
    """Test various AdaptiveRate configurations."""
    from pydynox.rate_limit import AdaptiveRate

    limiter = AdaptiveRate(max_rcu=max_rcu, max_wcu=max_wcu, min_rcu=min_rcu)
    assert limiter.max_rcu == max_rcu
    assert limiter.max_wcu == max_wcu
    # Should start at 50% of max
    assert limiter.current_rcu == max_rcu * 0.5
