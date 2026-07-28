"""Building up aggregates with add() on attributes that don't exist yet."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class WalletAggregate(Model):
    model_config = ModelConfig(table="wallet-transaction-aggregates")

    wallet_id = StringAttribute(partition_key=True)
    currency = StringAttribute(sort_key=True)

    total_amount = NumberAttribute()
    transaction_count = NumberAttribute()


async def main():
    # The aggregate item does not exist yet - no save() needed
    aggregate = WalletAggregate(wallet_id="wallet-123", currency="USD")

    # add() starts from zero, so this works on the first call
    await aggregate.update(
        atomic=[
            WalletAggregate.total_amount.add(25),
            WalletAggregate.transaction_count.add(1),
        ]
    )
    # total_amount: 25, transaction_count: 1

    # The same code keeps incrementing from there
    await aggregate.update(
        atomic=[
            WalletAggregate.total_amount.add(10),
            WalletAggregate.transaction_count.add(1),
        ]
    )
    # total_amount: 35, transaction_count: 2


asyncio.run(main())
