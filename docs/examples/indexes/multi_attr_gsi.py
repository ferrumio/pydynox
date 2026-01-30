from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class Product(Model):
    model_config = ModelConfig(table="products")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
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
        partition_key=["tenant_id", "region"],
        sort_key=["created_at", "item_id"],
    )

    # Multi-attribute GSI: 2 partition keys only
    category_index = GlobalSecondaryIndex(
        index_name="category-index",
        partition_key=["category", "subcategory"],
    )
