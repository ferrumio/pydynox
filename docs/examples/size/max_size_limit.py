from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.exceptions import ItemTooLargeException


class Comment(Model):
    model_config = ModelConfig(table="comments", max_size=10_000)  # 10KB limit

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    text = StringAttribute()


comment = Comment(
    pk="POST#1",
    sk="COMMENT#1",
    text="X" * 20_000,  # Too big!
)

try:
    comment.save()
except ItemTooLargeException as e:
    print(f"Item too large: {e.size} bytes")
    print(f"Max allowed: {e.max_size} bytes")
    print(f"Item key: {e.item_key}")
