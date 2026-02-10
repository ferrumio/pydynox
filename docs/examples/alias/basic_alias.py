from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

# Use readable Python names, store short names in DynamoDB


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute(alias="em")
    first_name = StringAttribute(alias="fn")
    last_name = StringAttribute(alias="ln")
    age = NumberAttribute(alias="a")


# Code is readable
user = User(
    pk="USER#1",
    sk="PROFILE",
    email="john@example.com",
    first_name="John",
    last_name="Doe",
    age=30,
)

# to_dict() uses alias names (what DynamoDB stores)
d = user.to_dict()
print(d)
# {"pk": "USER#1", "sk": "PROFILE", "em": "john@example.com", "fn": "John", "ln": "Doe", "a": 30}

assert d["em"] == "john@example.com"
assert d["fn"] == "John"
assert "email" not in d  # Python name is NOT in the dict
