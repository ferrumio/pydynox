from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Client-level sync batch get
keys = [
    {"pk": "USER#1", "sk": "PROFILE"},
    {"pk": "USER#2", "sk": "PROFILE"},
    {"pk": "USER#3", "sk": "PROFILE"},
]
items = client.sync_batch_get("users", keys)
for item in items:
    print(item["name"])

# Model-level sync batch get - returns typed instances
users = User.sync_batch_get(keys)
for user in users:
    print(user.name, user.age)

# Return as dicts for better performance
users_dict = User.sync_batch_get(keys, as_dict=True)
for user in users_dict:
    print(user["name"])
