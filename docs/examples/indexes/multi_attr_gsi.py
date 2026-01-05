from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    tenant_id = StringAttribute()
    region = StringAttribute()
    created_at = StringAttribute()
    item_id = StringAttribute()
    category = StringAttribute()
    subcategory = StringAttribute()
    name = StringAttribute()
    price = NumberAttribute()

    # Multi-attribute GSI: 2 partition keys + 2 sort keys
    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        hash_key=["tenant_id", "region"],
        range_key=["created_at", "item_id"],
    )

    # Multi-attribute GSI: 2 partition keys only
    category_index = GlobalSecondaryIndex(
        index_name="category-index",
        hash_key=["category", "subcategory"],
    )
