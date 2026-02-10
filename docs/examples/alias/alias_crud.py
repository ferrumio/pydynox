import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)
    product_name = StringAttribute(alias="pn")
    price = NumberAttribute(alias="pr")
    stock = NumberAttribute(alias="stk")


async def main():
    # Save — Python names in code, short names in DynamoDB
    laptop = Product(pk="PROD#1", product_name="Laptop", price=999, stock=10)
    await laptop.save()

    # Get — alias names are translated back to Python names
    loaded = await Product.get(pk="PROD#1")
    assert loaded is not None
    print(f"Name: {loaded.product_name}")  # "Laptop"
    print(f"Price: {loaded.price}")  # 999

    # Update — use Python names
    await loaded.update(price=899)

    # Verify
    updated = await Product.get(pk="PROD#1")
    assert updated is not None
    print(f"New price: {updated.price}")  # 899


asyncio.run(main())
