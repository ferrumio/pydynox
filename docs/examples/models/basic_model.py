from pydynox import Model
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute


class User(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
    active = BooleanAttribute(default=True)
