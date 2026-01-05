"""Parallel scan for large tables."""

import concurrent.futures

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()


def scan_segment(segment: int, total: int) -> list[User]:
    """Scan a single segment."""
    return list(User.scan(segment=segment, total_segments=total))


# Parallel scan with 4 workers
total_segments = 4

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(scan_segment, i, total_segments) for i in range(total_segments)]

    all_users: list[User] = []
    for future in concurrent.futures.as_completed(futures):
        all_users.extend(future.result())

print(f"Total users found: {len(all_users)}")
