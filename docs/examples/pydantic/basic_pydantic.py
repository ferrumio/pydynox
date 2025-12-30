from pydantic import BaseModel, EmailStr
from pydynox.integrations.pydantic import dynamodb_model


@dynamodb_model(table="users", hash_key="pk")
class User(BaseModel):
    pk: str
    name: str
    email: EmailStr
    age: int = 0


# Pydantic validation works
user = User(pk="USER#1", name="John", email="john@test.com")
user.save()

# Get
user = User.get(pk="USER#1")
print(user.email)
