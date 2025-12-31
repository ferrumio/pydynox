"""JSONAttribute example - store dict/list as JSON string."""

from pydynox import Model, ModelConfig
from pydynox.attributes import JSONAttribute, StringAttribute


class Config(Model):
    model_config = ModelConfig(table="configs")

    pk = StringAttribute(hash_key=True)
    settings = JSONAttribute()


# Save a dict
config = Config(
    pk="CFG#1",
    settings={"theme": "dark", "notifications": True, "max_items": 50},
)
config.save()
# Stored as '{"theme": "dark", "notifications": true, "max_items": 50}'

# Load it back
loaded = Config.get(pk="CFG#1")
print(loaded.settings["theme"])  # "dark"

# Works with lists too
config2 = Config(pk="CFG#2", settings=["item1", "item2", "item3"])
config2.save()
