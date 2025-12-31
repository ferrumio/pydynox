"""EnumAttribute example - store Python enum as string."""

from enum import Enum

from pydynox import Model, ModelConfig
from pydynox.attributes import EnumAttribute, StringAttribute


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    status = EnumAttribute(Status, default=Status.PENDING)


# Create with enum value
user = User(pk="USER#1", status=Status.ACTIVE)
user.save()
# Stored as "active" in DynamoDB

# Load it back - returns the enum
loaded = User.get(pk="USER#1")
print(loaded.status)  # Status.ACTIVE
print(loaded.status == Status.ACTIVE)  # True

# Default value works
user2 = User(pk="USER#2")
print(user2.status)  # Status.PENDING
