"""Inventory management with atomic updates."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(hash_key=True)  # product_id
    stock = NumberAttribute()
    reserved = NumberAttribute()


class OutOfStock(Exception):
    pass


def reserve_stock(product: Product, quantity: int) -> None:
    """Reserve stock for an order."""
    try:
        product.update(
            atomic=[
                Product.stock.add(-quantity),
                Product.reserved.add(quantity),
            ],
            condition=Product.stock >= quantity,
        )
    except ConditionalCheckFailedException:
        raise OutOfStock(f"Not enough stock for {product.pk}")


def release_stock(product: Product, quantity: int) -> None:
    """Release reserved stock (order cancelled)."""
    product.update(
        atomic=[
            Product.stock.add(quantity),
            Product.reserved.add(-quantity),
        ]
    )


# Usage
product = Product(pk="SKU#ABC123", stock=10, reserved=0)
product.save()

# Reserve 3 units
reserve_stock(product, 3)
# stock: 7, reserved: 3

# Try to reserve 10 more - fails
try:
    reserve_stock(product, 10)
except OutOfStock:
    print("Cannot reserve - not enough stock")

# Cancel order - release the 3 units
release_stock(product, 3)
# stock: 10, reserved: 0
