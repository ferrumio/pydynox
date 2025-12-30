from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
    active = BooleanAttribute(default=True)
