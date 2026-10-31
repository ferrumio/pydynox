import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Counter(Model):
    model_config = ModelConfig(table="counters")
    pk = StringAttribute(partition_key=True)
    value = StringAttribute()
    version = VersionAttribute()


async def increment_with_retry(pk: str, max_retries: int = 5) -> Counter:
    """Increment counter with retry on conflict."""
    for attempt in range(max_retries):
        counter = await Counter.get(pk=pk)
        if counter is None:
            counter = Counter(pk=pk, value="0")

        counter.value = str(int(counter.value or "0") + 1)

        try:
            await counter.save()
            return counter
        except ConditionalCheckFailedException:
            if attempt == max_retries - 1:
                raise
            # Small delay before retry
            await asyncio.sleep(0.01 * (attempt + 1))

    raise RuntimeError("Should not reach here")


async def main():
    # Create counter
    counter = Counter(pk="COUNTER#1", value="0")
    await counter.save()

    # Run 10 concurrent increments
    tasks = [increment_with_retry("COUNTER#1") for _ in range(10)]
    await asyncio.gather(*tasks)

    # Final value should be 10
    final = await Counter.get(pk="COUNTER#1")
    assert final is not None
    print(f"Final value: {final.value}")  # 10
    print(f"Final version: {final.version}")  # 11 (1 create + 10 updates)


if __name__ == "__main__":
    asyncio.run(main())
