"""Atomic counter example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class PageView(Model):
    model_config = ModelConfig(table="analytics")

    pk = StringAttribute(hash_key=True)  # page_url
    sk = StringAttribute(range_key=True)  # date
    views = NumberAttribute()


# Increment counter without reading first
page = PageView(pk="/home", sk="2024-01-15", views=0)
page.save()

# Each request increments atomically
page.update(atomic=[PageView.views.add(1)])

# Multiple increments are safe - no race conditions
# Request 1: views = 0 + 1 = 1
# Request 2: views = 1 + 1 = 2
# Request 3: views = 2 + 1 = 3
