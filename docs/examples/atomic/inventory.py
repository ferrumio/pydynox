"""Inventory management with atomic updates."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)  # product_id
    stock = NumberAttribute()
    reserved = NumberAttribute()


class OutOfStock(Exception):
    pass


async def reserve_stock(product: Product, quantity: int) -> None:
    """Reserve stock for an order."""
    try:
        await product.update(
            atomic=[
                Product.stock.add(-quantity),
                Product.reserved.add(quantity),
            ],
            condition=Product.stock >= quantity,
        )
    except ConditionalCheckFailedException:
        raise OutOfStock(f"Not enough stock for {product.pk}")


async def release_stock(product: Product, quantity: int) -> None:
    """Release reserved stock (order cancelled)."""
    await product.update(
        atomic=[
            Product.stock.add(quantity),
            Product.reserved.add(-quantity),
        ]
    )


async def main():
    # Usage
    product = Product(pk="SKU#ABC123", stock=10, reserved=0)
    await product.save()

    # Reserve 3 units
    await reserve_stock(product, 3)
    # stock: 7, reserved: 3

    # Try to reserve 10 more - fails
    try:
        await reserve_stock(product, 10)
    except OutOfStock:
        print("Cannot reserve - not enough stock")

    # Cancel order - release the 3 units
    await release_stock(product, 3)
    # stock: 10, reserved: 0


asyncio.run(main())
