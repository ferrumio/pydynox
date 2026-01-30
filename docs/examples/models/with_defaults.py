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

    pk = StringAttribute(partition_key=True)
    email = StringAttribute(required=True)  # Required field
    name = StringAttribute(default="")
    age = NumberAttribute(default=0)
    active = BooleanAttribute(default=True)
    tags = ListAttribute(default=[])
    settings = MapAttribute(default={})
