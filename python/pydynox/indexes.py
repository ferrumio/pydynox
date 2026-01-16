"""Secondary Index support for pydynox models.

GSIs allow querying by non-key attributes. Define them on your model
and query using the index's partition key.

LSIs allow querying by the same hash key but a different sort key.
They must be created with the table and share the table's hash key.

Example:
    >>> from pydynox import Model, ModelConfig
    >>> from pydynox.attributes import StringAttribute
    >>> from pydynox.indexes import GlobalSecondaryIndex, LocalSecondaryIndex
    >>>
    >>> class User(Model):
    ...     model_config = ModelConfig(table="users")
    ...     pk = StringAttribute(hash_key=True)
    ...     sk = StringAttribute(range_key=True)
    ...     email = StringAttribute()
    ...     status = StringAttribute()
    ...
    ...     # GSI - different hash key
    ...     email_index = GlobalSecondaryIndex(
    ...         index_name="email-index",
    ...         hash_key="email",
    ...     )
    ...
    ...     # LSI - same hash key, different sort key
    ...     status_index = LocalSecondaryIndex(
    ...         index_name="status-index",
    ...         range_key="status",
    ...     )
    >>>
    >>> # Query GSI
    >>> for user in User.email_index.query(email="john@example.com"):
    ...     print(user.pk)
    >>>
    >>> # Query LSI (uses table's hash key)
    >>> for user in User.status_index.query(pk="USER#1"):
    ...     print(user.status)
"""

from pydynox._internal._indexes import GlobalSecondaryIndex, LocalSecondaryIndex

__all__ = ["GlobalSecondaryIndex", "LocalSecondaryIndex"]
