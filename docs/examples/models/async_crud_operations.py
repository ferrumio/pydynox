from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Create
    user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
    await user.async_save()

    # Read
    user = await User.async_get(pk="USER#123", sk="PROFILE")
    if user:
        print(user.name)  # John

    # Update - full
    user.name = "Jane"
    await user.async_save()

    # Update - partial
    await user.async_update(name="Jane", age=31)

    # Delete
    await user.async_delete()
