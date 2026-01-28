"""Complex business rules with combined conditions."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute


class Account(Model):
    model_config = ModelConfig(table="accounts")

    pk = StringAttribute(hash_key=True)
    balance = NumberAttribute()
    status = StringAttribute()
    verified = BooleanAttribute()


async def main():
    # Create account first
    account = Account(pk="ACC#123", balance=500, status="active", verified=True)
    await account.save()

    # Only allow withdrawal if:
    # - Account is active AND verified
    # - Balance is sufficient
    withdrawal = 100

    condition = (
        (Account.status == "active")
        & (Account.verified == True)  # noqa: E712
        & (Account.balance >= withdrawal)
    )

    account.balance = account.balance - withdrawal
    await account.save(condition=condition)


asyncio.run(main())
