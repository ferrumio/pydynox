"""Optimistic locking - only update if version matches."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    price = NumberAttribute()
    version = NumberAttribute()


# Create product first
product = Product(pk="PROD#123", name="Widget", price=19.99, version=1)
product.save()

# Get current product
product = Product.get(pk="PROD#123")
current_version = product.version

# Update with version check
product.price = 29.99
product.version = current_version + 1
product.save(condition=Product.version == current_version)

# If someone else updated the product, version won't match
# and ConditionalCheckFailedException is raised
