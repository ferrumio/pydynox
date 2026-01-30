"""FastAPI example (async is default - no prefix needed)."""

from fastapi import FastAPI
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute

app = FastAPI()
client = DynamoDBClient()
set_default_client(client)


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await User.get(pk=f"USER#{user_id}", sk="PROFILE")
    if not user:
        return {"error": "User not found"}
    return {"name": user.name}


@app.post("/users/{user_id}")
async def create_user(user_id: str, name: str):
    user = User(pk=f"USER#{user_id}", sk="PROFILE", name=name)
    await user.save()
    return {"status": "created"}
