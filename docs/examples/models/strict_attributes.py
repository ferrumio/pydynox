"""Catch misspelled field names before making a database request."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users", strict_attributes=True)
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


try:
    User(pk="USER#1", naem="Bob")
except AttributeError as error:
    print(error)  # User has no attribute 'naem'

user = User(pk="USER#1", name="Alice")
user.name = "Bob"  # Declared field: accepted

try:
    user.naem = "Bob"
except AttributeError as error:
    print(error)  # User has no attribute 'naem'

user._cache = {}  # Private application state is allowed and is not saved
