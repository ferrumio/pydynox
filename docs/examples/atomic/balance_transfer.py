"""Safe balance transfer with condition."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Account(Model):
    model_config = ModelConfig(table="accounts")

    pk = StringAttribute(partition_key=True)  # account_id
    balance = NumberAttribute()


async def withdraw(account: Account, amount: int) -> bool:
    """Withdraw money only if balance is sufficient."""
    try:
        await account.update(
            atomic=[Account.balance.add(-amount)],
            condition=Account.balance >= amount,
        )
        return True
    except ConditionalCheckFailedException:
        return False


async def main():
    # Usage
    account = Account(pk="ACC#123", balance=100)
    await account.save()

    # This succeeds - balance goes from 100 to 50
    success = await withdraw(account, 50)
    print(f"Withdrew 50: {success}")  # True

    # This fails - balance is 50, can't withdraw 75
    success = await withdraw(account, 75)
    print(f"Withdrew 75: {success}")  # False


asyncio.run(main())
