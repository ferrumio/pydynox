"""StringSetAttribute and NumberSetAttribute examples."""

from pydynox import Model, ModelConfig
from pydynox.attributes import (
    NumberSetAttribute,
    StringAttribute,
    StringSetAttribute,
)


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    tags = StringSetAttribute()
    scores = NumberSetAttribute()


# Create with sets
user = User(
    pk="USER#SET",
    sk="PROFILE",
    tags={"admin", "verified", "premium"},
    scores={100, 95, 88},
)
user.save()

# Load it back - returns Python sets
loaded = User.get(pk="USER#SET", sk="PROFILE")
print(loaded.tags)  # {'admin', 'verified', 'premium'}
print(loaded.scores)  # {100, 95, 88}

# Check membership
print("admin" in loaded.tags)  # True
print(100 in loaded.scores)  # True

# Sets don't allow duplicates
user2 = User(pk="USER#SET2", sk="PROFILE", tags={"a", "a", "b"})
print(user2.tags)  # {'a', 'b'}
