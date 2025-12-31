"""Managing user tags with list operations."""

from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    tags = ListAttribute()


# Create user with initial tags
user = User(pk="USER#123", sk="PROFILE", tags=["member"])
user.save()

# Add tags to the end
user.update(atomic=[User.tags.append(["premium", "verified"])])
# tags: ["member", "premium", "verified"]

# Add tags to the beginning
user.update(atomic=[User.tags.prepend(["vip"])])
# tags: ["vip", "member", "premium", "verified"]
