from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.hooks import (
    after_delete,
    after_load,
    after_save,
    after_update,
    before_delete,
    before_save,
    before_update,
)


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()

    @before_save
    def on_before_save(self):
        print("Before save")

    @after_save
    def on_after_save(self):
        print("After save")

    @before_delete
    def on_before_delete(self):
        print("Before delete")

    @after_delete
    def on_after_delete(self):
        print("After delete")

    @before_update
    def on_before_update(self):
        print("Before update")

    @after_update
    def on_after_update(self):
        print("After update")

    @after_load
    def on_after_load(self):
        print("After load (get or query)")
