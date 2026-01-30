"""API rate limiting with atomic counters."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class ApiUsage(Model):
    model_config = ModelConfig(table="api_usage")

    pk = StringAttribute(partition_key=True)  # user_id
    sk = StringAttribute(sort_key=True)  # date (YYYY-MM-DD)
    requests = NumberAttribute()


class RateLimitExceeded(Exception):
    pass


async def track_request(user_id: str, date: str, daily_limit: int = 1000) -> int:
    """Track API request and enforce rate limit.

    Returns the new request count.
    Raises RateLimitExceeded if over limit.
    """
    usage = await ApiUsage.get(pk=user_id, sk=date)

    if usage is None:
        # First request of the day
        usage = ApiUsage(pk=user_id, sk=date, requests=1)
        await usage.save()
        return 1

    try:
        await usage.update(
            atomic=[ApiUsage.requests.add(1)],
            condition=ApiUsage.requests < daily_limit,
        )
        # Fetch updated count
        updated = await ApiUsage.get(pk=user_id, sk=date)
        return updated.requests
    except ConditionalCheckFailedException:
        raise RateLimitExceeded(f"User {user_id} exceeded {daily_limit} requests/day")


async def main():
    try:
        count = await track_request("user_123", "2024-01-15")
        print(f"Request #{count} recorded")
    except RateLimitExceeded as e:
        print(f"Rate limit hit: {e}")


asyncio.run(main())
