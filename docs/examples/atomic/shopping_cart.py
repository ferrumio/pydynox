"""Shopping cart with list operations."""

from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute


class Cart(Model):
    model_config = ModelConfig(table="carts")

    pk = StringAttribute(hash_key=True)  # user_id
    sk = StringAttribute(range_key=True)  # "CART"
    items = ListAttribute()
    total = NumberAttribute()


def add_to_cart(cart: Cart, item: dict, price: float) -> None:
    """Add item to cart and update total."""
    cart.update(
        atomic=[
            Cart.items.append([item]),
            Cart.total.add(price),
        ]
    )


def apply_discount(cart: Cart, discount: float) -> None:
    """Apply discount to cart total."""
    cart.update(
        atomic=[Cart.total.add(-discount)],
        condition=Cart.total >= discount,
    )


# Usage
cart = Cart(pk="USER#123", sk="CART", items=[], total=0)
cart.save()

# Add items
add_to_cart(cart, {"sku": "SHIRT-M", "qty": 1}, 29.99)
add_to_cart(cart, {"sku": "PANTS-L", "qty": 2}, 49.99)

# Cart now has:
# items: [{"sku": "SHIRT-M", "qty": 1}, {"sku": "PANTS-L", "qty": 2}]
# total: 79.98

# Apply $10 discount
apply_discount(cart, 10.00)
# total: 69.98
