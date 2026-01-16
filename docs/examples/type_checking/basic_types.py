"""Basic type checking example - attribute types."""

from pydynox import Model, ModelConfig
from pydynox.attributes import (
    BooleanAttribute,
    NumberAttribute,
    StringAttribute,
)


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    active = BooleanAttribute()


user = User(pk="USER#1", name="John", age=30, active=True)

# On instance: returns the value (T | None)
pk_value: str | None = user.pk
name_value: str | None = user.name
age_value: float | None = user.age
active_value: bool | None = user.active

# On class: returns the Attribute (for conditions)
# User.pk -> StringAttribute
# User.pk == "USER#1" -> Condition
