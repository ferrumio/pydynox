"""API rate limiting with atomic counters."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionCheckFailedError


class ApiUsage(Model):
    model_config = ModelConfig(table="api_usage")

    pk = StringAttribute(hash_key=True)  # user_id
    sk = StringAttribute(range_key=True)  # date (YYYY-MM-DD)
    requests = NumberAttribute()


class RateLimitExceeded(Exception):
    pass


def track_request(user_id: str, date: str, daily_limit: int = 1000) -> int:
    """Track API request and enforce rate limit.

    Returns the new request count.
    Raises RateLimitExceeded if over limit.
    """
    usage = ApiUsage.get(pk=user_id, sk=date)

    if usage is None:
        # First request of the day
        usage = ApiUsage(pk=user_id, sk=date, requests=1)
        usage.save()
        return 1

    try:
        usage.update(
            atomic=[ApiUsage.requests.add(1)],
            condition=ApiUsage.requests < daily_limit,
        )
        # Fetch updated count
        updated = ApiUsage.get(pk=user_id, sk=date)
        return updated.requests
    except ConditionCheckFailedError:
        raise RateLimitExceeded(f"User {user_id} exceeded {daily_limit} requests/day")


# Usage
try:
    count = track_request("user_123", "2024-01-15")
    print(f"Request #{count} recorded")
except RateLimitExceeded as e:
    print(f"Rate limit hit: {e}")
