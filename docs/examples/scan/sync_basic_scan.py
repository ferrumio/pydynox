"""Basic scan example - scan all items in a table (sync - use sync_ prefix)."""

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def main():
    # Scan all users
    for user in User.sync_scan():
        print(f"{user.name} is {user.age} years old")


main()
