"""Prevent overwriting existing items."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()


# Only save if the item doesn't exist yet
user = User(pk="USER#NEW", sk="PROFILE", email="john@example.com", name="John", age=30)
user.save(condition=User.pk.does_not_exist())

# If USER#NEW already exists, this raises ConditionCheckFailedError
