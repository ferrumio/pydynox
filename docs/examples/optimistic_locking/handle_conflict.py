from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionCheckFailedError


class Counter(Model):
    model_config = ModelConfig(table="counters")
    pk = StringAttribute(hash_key=True)
    count = NumberAttribute()
    version = VersionAttribute()


def increment_with_retry(pk: str, max_retries: int = 3) -> Counter:
    """Increment counter with retry on conflict."""
    for attempt in range(max_retries):
        counter = Counter.get(pk=pk)
        if counter is None:
            counter = Counter(pk=pk, count=0)

        # Increment
        counter.count = counter.count + 1

        try:
            counter.save()
            return counter
        except ConditionCheckFailedError:
            if attempt == max_retries - 1:
                raise
            print(f"Conflict on attempt {attempt + 1}, retrying...")

    raise RuntimeError("Should not reach here")


# Usage
counter = increment_with_retry("COUNTER#RETRY")
print(f"Count: {counter.count}, Version: {counter.version}")
