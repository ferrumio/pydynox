"""Store exact amounts with DecimalAttribute (async)."""

import asyncio
from decimal import Decimal

from pydynox import Model, ModelConfig
from pydynox.attributes import DecimalAttribute, NumberAttribute, StringAttribute


class Account(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    balance = DecimalAttribute()
    visits = NumberAttribute(default=0)


async def main():
    amount = Decimal("123456789.123456789")
    account = Account(pk="ACCOUNT#DECIMAL", sk="BALANCE", balance=amount, visits=1)
    await account.save()

    loaded = await Account.get(pk=account.pk, sk=account.sk)
    assert loaded.balance == amount
    assert type(loaded.balance) is Decimal
    assert type(loaded.visits) is int

    await loaded.update(atomic=[Account.balance.add(Decimal("0.000000001"))])
    updated = await Account.get(pk=account.pk, sk=account.sk)
    assert updated.balance == Decimal("123456789.123456790")
    await updated.delete()


asyncio.run(main())
