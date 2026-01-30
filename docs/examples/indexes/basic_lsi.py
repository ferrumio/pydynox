"""Basic LSI definition - query by same hash key with different sort key."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex


class Order(Model):
    """Order model with LSI for querying by status."""

    model_config = ModelConfig(table="orders")

    # Primary key: customer_id (hash) + order_id (range)
    customer_id = StringAttribute(partition_key=True)
    order_id = StringAttribute(sort_key=True)

    # Other attributes
    status = StringAttribute()
    total = NumberAttribute()
    created_at = StringAttribute()

    # LSI: query orders by customer_id + status
    # Same hash key (customer_id), different sort key (status)
    status_index = LocalSecondaryIndex(
        index_name="status-index",
        sort_key="status",
    )

    # LSI: query orders by customer_id + created_at
    created_index = LocalSecondaryIndex(
        index_name="created-index",
        sort_key="created_at",
    )
