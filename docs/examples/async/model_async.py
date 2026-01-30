"""Model async operations (async is default - no prefix needed)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def main():
    # Create and save
    user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
    await user.save()

    # Get by key
    user = await User.get(pk="USER#123", sk="PROFILE")

    # Update
    await user.update(name="Jane", age=31)

    # Delete
    await user.delete()
