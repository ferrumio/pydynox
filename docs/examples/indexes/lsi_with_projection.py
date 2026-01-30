"""LSI with different projection types."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex


class Order(Model):
    """Order model with LSIs using different projections."""

    model_config = ModelConfig(table="orders_projections")

    customer_id = StringAttribute(partition_key=True)
    order_id = StringAttribute(sort_key=True)
    status = StringAttribute()
    total = NumberAttribute()
    notes = StringAttribute()

    # ALL projection - includes all attributes
    status_index = LocalSecondaryIndex(
        index_name="status-index",
        sort_key="status",
        projection="ALL",
    )

    # KEYS_ONLY projection - only key attributes
    # Smaller index, faster queries when you only need keys
    total_index = LocalSecondaryIndex(
        index_name="total-index",
        sort_key="total",
        projection="KEYS_ONLY",
    )

    # INCLUDE projection - keys + specific attributes
    # Balance between size and data availability
    notes_index = LocalSecondaryIndex(
        index_name="notes-index",
        sort_key="notes",
        projection=["status", "total"],  # Include these non-key attributes
    )
