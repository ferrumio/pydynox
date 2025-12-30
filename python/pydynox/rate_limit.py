"""Rate limiting for DynamoDB operations.

Provides token bucket-based rate limiting to prevent throttling.
Two strategies are available:

- FixedRate: Use when you know exactly how much capacity to use
- AdaptiveRate: Auto-adjusts based on throttling feedback

Example:
    >>> from pydynox import DynamoDBClient, FixedRate
    >>> client = DynamoDBClient(rate_limit=FixedRate(rcu=50))
    >>> # All operations now respect the 50 RCU limit

    >>> from pydynox import AdaptiveRate
    >>> client = DynamoDBClient(rate_limit=AdaptiveRate(max_rcu=100))
    >>> # Rate auto-adjusts based on throttling
"""

from pydynox import pydynox_core

# Re-export Rust classes
FixedRate = pydynox_core.FixedRate
AdaptiveRate = pydynox_core.AdaptiveRate
RateLimitMetrics = pydynox_core.RateLimitMetrics

# Add docstrings for IDE support
FixedRate.__doc__ = """Fixed rate limiter.

Use when you know exactly how much capacity to use.
The rate stays constant unless you change it manually.

Args:
    rcu: Read capacity units per second (optional).
    wcu: Write capacity units per second (optional).
    burst: Burst capacity. Defaults to rate value if not set.

Attributes:
    rcu: The configured RCU rate.
    wcu: The configured WCU rate.
    consumed_rcu: Total RCU consumed so far.
    consumed_wcu: Total WCU consumed so far.
    throttle_count: Number of times throttled.

Example:
    >>> # Read only
    >>> FixedRate(rcu=50)

    >>> # Read and write
    >>> FixedRate(rcu=50, wcu=25)

    >>> # With burst (DynamoDB allows short bursts)
    >>> FixedRate(rcu=50, burst=200)
"""

AdaptiveRate.__doc__ = """Adaptive rate limiter that adjusts based on throttling.

Starts at 50% of max rate. When throttled, reduces by 20%.
When no throttle for 10 seconds, increases by 10%.

Args:
    max_rcu: Maximum read capacity units per second.
    max_wcu: Maximum write capacity units per second (optional).
    min_rcu: Minimum RCU, won't go below this (default: 1).
    min_wcu: Minimum WCU, won't go below this (default: 1).

Attributes:
    current_rcu: Current RCU rate (changes based on throttling).
    current_wcu: Current WCU rate (changes based on throttling).
    max_rcu: Maximum RCU configured.
    max_wcu: Maximum WCU configured.
    consumed_rcu: Total RCU consumed so far.
    consumed_wcu: Total WCU consumed so far.
    throttle_count: Number of times throttled.

Example:
    >>> # Just set the max, it figures out the rest
    >>> AdaptiveRate(max_rcu=100)

    >>> # With write limit too
    >>> AdaptiveRate(max_rcu=100, max_wcu=50)

    >>> # Custom min (won't go below this)
    >>> AdaptiveRate(max_rcu=100, min_rcu=10)
"""

RateLimitMetrics.__doc__ = """Metrics for monitoring rate limiter behavior.

Attributes:
    consumed_rcu: Total RCU consumed.
    consumed_wcu: Total WCU consumed.
    throttle_count: Number of times throttled.

Methods:
    reset(): Reset all metrics to zero.
"""

__all__ = [
    "FixedRate",
    "AdaptiveRate",
    "RateLimitMetrics",
]
