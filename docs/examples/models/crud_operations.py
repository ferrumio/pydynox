from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


# Create
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
user.save()

# Read
user = User.get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)  # John

# Update - full
user.name = "Jane"
user.save()

# Update - partial
user.update(name="Jane", age=31)

# Delete
user.delete()
