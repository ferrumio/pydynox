from pydynox import Model, ModelConfig
from pydynox.attributes import (
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
)


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    email = StringAttribute(null=False)  # Required field
    name = StringAttribute(default="")
    age = NumberAttribute(default=0)
    active = BooleanAttribute(default=True)
    tags = ListAttribute(default=[])
    settings = MapAttribute(default={})
