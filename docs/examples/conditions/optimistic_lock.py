"""Optimistic locking - only update if version matches."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    price = NumberAttribute()
    version = NumberAttribute()


async def main():
    # Create product first
    product = Product(pk="PROD#123", name="Widget", price=19.99, version=1)
    await product.save()

    # Get current product
    product = await Product.get(pk="PROD#123")
    current_version = product.version

    # Update with version check
    product.price = 29.99
    product.version = current_version + 1
    await product.save(condition=Product.version == current_version)

    # If someone else updated the product, version won't match
    # and ConditionalCheckFailedException is raised


asyncio.run(main())
