"""Example: Follower/following social pattern."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class Follow(Model):
    model_config = ModelConfig(table="social")

    # Main: pk=FOLLOWER#alice, sk=FOLLOWING#bob
    pk = StringAttribute(partition_key=True, template="FOLLOWER#{follower}")
    sk = StringAttribute(sort_key=True, template="FOLLOWING#{following}")
    follower = StringAttribute()
    following = StringAttribute()

    # Inverted: pk=FOLLOWING#bob, sk=FOLLOWER#alice
    followers_index = GlobalSecondaryIndex(
        index_name="followers",
        partition_key="sk",
        sort_key="pk",
    )


async def main():
    # Alice follows Bob and Charlie
    f1 = Follow(follower="alice", following="bob")
    f2 = Follow(follower="alice", following="charlie")
    # Dave follows Bob
    f3 = Follow(follower="dave", following="bob")
    await f1.save()
    await f2.save()
    await f3.save()

    # Who does Alice follow? (main table)
    print("Alice follows:")
    async for f in Follow.query(follower="alice"):
        print(f"  {f.following}")

    # Who follows Bob? (inverted index)
    print("\nBob's followers:")
    async for f in Follow.followers_index.query(following="bob"):
        print(f"  {f.follower}")

    # Cleanup
    await f1.delete()
    await f2.delete()
    await f3.delete()


if __name__ == "__main__":
    asyncio.run(main())
