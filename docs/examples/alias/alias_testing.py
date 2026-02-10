from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute(alias="em")
    age = NumberAttribute(alias="a")


@MemoryBackend()
def test_alias_roundtrip():
    user = User(pk="USER#1", sk="PROFILE", email="test@example.com", age=25)
    user.sync_save()

    loaded = User.sync_get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.email == "test@example.com"
    assert loaded.age == 25


@MemoryBackend()
def test_alias_to_dict():
    user = User(pk="USER#1", sk="PROFILE", email="test@example.com", age=25)

    d = user.to_dict()
    # Alias names in the dict
    assert d["em"] == "test@example.com"
    assert d["a"] == 25
    # Python names NOT in the dict
    assert "email" not in d
    assert "age" not in d


test_alias_roundtrip()
test_alias_to_dict()
print("All alias tests passed!")
