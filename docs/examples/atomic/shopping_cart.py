"""Shopping cart with list operations."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute


class Cart(Model):
    model_config = ModelConfig(table="carts")

    pk = StringAttribute(hash_key=True)  # user_id
    items = ListAttribute()
    total = NumberAttribute()


async def add_to_cart(cart: Cart, item: dict, price: float) -> None:
    """Add item to cart and update total."""
    await cart.update(
        atomic=[
            Cart.items.append([item]),
            Cart.total.add(price),
        ]
    )


async def apply_discount(cart: Cart, discount: float) -> None:
    """Apply discount to cart total."""
    await cart.update(
        atomic=[Cart.total.add(-discount)],
        condition=Cart.total >= discount,
    )


async def main():
    # Usage
    cart = Cart(pk="USER#123", items=[], total=0)
    await cart.save()

    # Add items
    await add_to_cart(cart, {"sku": "SHIRT-M", "qty": 1}, 29.99)
    await add_to_cart(cart, {"sku": "PANTS-L", "qty": 2}, 49.99)

    # Cart now has:
    # items: [{"sku": "SHIRT-M", "qty": 1}, {"sku": "PANTS-L", "qty": 2}]
    # total: 79.98

    # Apply $10 discount
    await apply_discount(cart, 10.00)
    # total: 69.98


asyncio.run(main())
