from pydantic import BaseModel, EmailStr
from pydynox import get_default_client
from pydynox.integrations.pydantic import dynamodb_model

# Get the default client (assumes set_default_client was called)
client = get_default_client()


@dynamodb_model(table="users", hash_key="pk", range_key="sk", client=client)
class User(BaseModel):
    pk: str
    sk: str
    name: str
    email: EmailStr
    age: int = 0


# Pydantic validation works
user = User(pk="USER#1", sk="PROFILE", name="John", email="john@test.com")
user.save()

# Get
user = User.get(pk="USER#1", sk="PROFILE")
print(user.name)
