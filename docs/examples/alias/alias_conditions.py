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
    product = Product(pk="PROD#COND", product_name="Mouse", price=25, stock=100)
    await product.save()

    # Conditions use Python names — alias is handled automatically
    await product.update(
        stock=99,
        condition=Product.stock > 0,
    )
    # DynamoDB sees: SET #n0 = :v0 WHERE #n1 > :v1
    # Where #n0 = "stk", #n1 = "stk"

    # exists / not_exists
    await product.save(condition=Product.product_name.exists())

    # begins_with
    products = [
        p
        async for p in Product.scan(
            filter_condition=Product.product_name.begins_with("Mo"),
        )
    ]
    print(f"Found {len(products)} products starting with 'Mo'")


asyncio.run(main())
