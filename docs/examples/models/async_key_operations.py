from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Update without fetching first - one DynamoDB call
    await User.async_update_by_key(pk="USER#123", sk="PROFILE", name="Jane")

    # Delete without fetching first - one DynamoDB call
    await User.async_delete_by_key(pk="USER#123", sk="PROFILE")
