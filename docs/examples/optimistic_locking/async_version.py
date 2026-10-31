import asyncio
from random import uniform
from uuid import uuid4

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Counter(Model):
    model_config = ModelConfig(table="counters")
    pk = StringAttribute(partition_key=True)
    value = StringAttribute()
    version = VersionAttribute()


async def increment_with_retry(pk: str, max_retries: int = 20) -> Counter:
    """Increment counter with retry on conflict."""
    for attempt in range(max_retries):
        counter = await Counter.get(pk=pk, consistent_read=True)
        if counter is None:
            counter = Counter(pk=pk, value="0")

        counter.value = str(int(counter.value or "0") + 1)

        try:
            await counter.save()
            return counter
        except ConditionalCheckFailedException:
            if attempt == max_retries - 1:
                raise
            # Random delays keep competing writers from retrying together.
            delay = min(0.01 * 2**attempt, 0.5)
            await asyncio.sleep(uniform(0, delay))

    raise RuntimeError("Should not reach here")


async def main() -> None:
    # Create counter
    pk = f"COUNTER#{uuid4()}"
    counter = Counter(pk=pk, value="0")
    await counter.save()

    # Run 10 concurrent increments
    tasks = [increment_with_retry(pk) for _ in range(10)]
    await asyncio.gather(*tasks)

    # Final value should be 10
    final = await Counter.get(pk=pk, consistent_read=True)
    assert final is not None
    assert final.value == "10"
    assert final.version == 11
    print(f"Final value: {final.value}")  # 10
    print(f"Final version: {final.version}")  # 11 (1 create + 10 updates)


asyncio.run(main())
