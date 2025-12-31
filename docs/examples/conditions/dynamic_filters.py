"""Build conditions dynamically from user input."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.conditions import And


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(hash_key=True)
    category = StringAttribute()
    price = NumberAttribute()
    brand = StringAttribute()


def build_product_filter(
    category: str | None = None,
    max_price: float | None = None,
    brand: str | None = None,
):
    """Build filter from optional parameters."""
    conditions = []

    if category:
        conditions.append(Product.category == category)
    if max_price:
        conditions.append(Product.price <= max_price)
    if brand:
        conditions.append(Product.brand == brand)

    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]

    return And(*conditions)


# User searches for electronics under $500
filter_cond = build_product_filter(category="electronics", max_price=500)
