"""Complex business rules with combined conditions."""

from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute


class Account(Model):
    model_config = ModelConfig(table="accounts")

    pk = StringAttribute(hash_key=True)
    balance = NumberAttribute()
    status = StringAttribute()
    verified = BooleanAttribute()


# Only allow withdrawal if:
# - Account is active AND verified
# - Balance is sufficient
account = Account.get(pk="ACC#123")
withdrawal = 100

condition = (
    (Account.status == "active")
    & (Account.verified == True)  # noqa: E712
    & (Account.balance >= withdrawal)
)

account.balance = account.balance - withdrawal
account.save(condition=condition)
