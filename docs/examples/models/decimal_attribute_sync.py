"""Store exact amounts with DecimalAttribute (sync)."""

from decimal import Decimal

from pydynox import Model, ModelConfig
from pydynox.attributes import DecimalAttribute, NumberAttribute, StringAttribute


class Account(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    balance = DecimalAttribute()
    visits = NumberAttribute(default=0)


amount = Decimal("123456789.123456789")
account = Account(pk="ACCOUNT#DECIMAL-SYNC", sk="BALANCE", balance=amount, visits=1)
account.sync_save()

loaded = Account.sync_get(pk=account.pk, sk=account.sk)
assert loaded.balance == amount
assert type(loaded.balance) is Decimal
assert type(loaded.visits) is int

loaded.sync_update(atomic=[Account.balance.add(Decimal("0.000000001"))])
updated = Account.sync_get(pk=account.pk, sk=account.sk)
assert updated.balance == Decimal("123456789.123456790")
updated.sync_delete()
