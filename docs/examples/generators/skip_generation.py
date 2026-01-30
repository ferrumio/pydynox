import asyncio

from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import StringAttribute


class Item(Model):
    model_config = ModelConfig(table="items")

    pk = StringAttribute(partition_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(sort_key=True)


async def main():
    # Auto-generate: don't provide pk
    item1 = Item(sk="DATA#1")
    await item1.save()
    print(item1.pk)  # "01HX5K3M2N4P5Q6R7S8T9UVWXY" (generated)

    # Skip auto-generate: provide your own pk
    item2 = Item(pk="CUSTOM#ID#123", sk="DATA#2")
    await item2.save()
    print(item2.pk)  # "CUSTOM#ID#123" (your value)


asyncio.run(main())
