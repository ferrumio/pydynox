"""Compare WCU consumed: smart save vs full replace."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    email = StringAttribute()
    bio = StringAttribute()
    address = StringAttribute()
    phone = StringAttribute()
    company = StringAttribute()


async def main():
    # Create a large item (~2KB)
    user = User(
        pk="USER#wcu",
        sk="PROFILE",
        name="John Doe",
        email="john@example.com",
        bio="A" * 1000,  # 1KB of data
        address="123 Main St, City, Country",
        phone="+1-555-0123",
        company="Acme Corp",
    )
    await user.save()

    # Reload to enable change tracking
    user = await User.get(pk="USER#wcu", sk="PROFILE")
    if not user:
        return

    # Test 1: Smart save (only changed field)
    User.reset_metrics()
    user.name = "Jane Doe"
    await user.save()
    smart_metrics = User.get_total_metrics()

    # Test 2: Full replace (all fields)
    User.reset_metrics()
    user.name = "Bob Smith"
    await user.save(full_replace=True)
    full_metrics = User.get_total_metrics()

    # Results
    print("=== WCU Comparison ===")
    print(f"Smart save (UpdateItem): {smart_metrics.total_wcu} WCU")
    print(f"Full replace (PutItem):  {full_metrics.total_wcu} WCU")
    print(f"Savings: {full_metrics.total_wcu - smart_metrics.total_wcu} WCU")

    # Cleanup
    await user.delete()


if __name__ == "__main__":
    asyncio.run(main())
