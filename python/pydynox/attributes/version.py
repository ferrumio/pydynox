"""Version attribute for optimistic locking."""

from __future__ import annotations

from typing import Any

from pydynox.attributes.base import Attribute


class VersionAttribute(Attribute[int]):
    """Version attribute for optimistic locking.

    Automatically increments on each save. When saving, pydynox adds a
    condition to check the version matches, preventing concurrent updates
    from overwriting each other.

    The version starts at 1 on first save. Each subsequent save increments
    it by 1 and checks that the current version in DynamoDB matches.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, VersionAttribute
        >>>
        >>> class Document(Model):
        ...     model_config = ModelConfig(table="documents")
        ...     pk = StringAttribute(partition_key=True)
        ...     content = StringAttribute()
        ...     version = VersionAttribute()
        >>>
        >>> # First save: version = 1
        >>> doc = Document(pk="DOC#1", content="Hello")
        >>> doc.save()
        >>> print(doc.version)  # 1
        >>>
        >>> # Second save: version = 2
        >>> doc.content = "Hello World"
        >>> doc.save()
        >>> print(doc.version)  # 2
        >>>
        >>> # Concurrent update fails
        >>> doc1 = Document.get(pk="DOC#1")  # version = 2
        >>> doc2 = Document.get(pk="DOC#1")  # version = 2
        >>> doc1.content = "Update 1"
        >>> doc1.save()  # OK, version = 3
        >>> doc2.content = "Update 2"
        >>> doc2.save()  # Raises ConditionalCheckFailedException!

    Note:
        - Version is auto-managed. Don't set it manually.
        - Works with save() and delete().
        - update() does NOT auto-increment version (use save() for versioning).
    """

    attr_type = "N"

    def __init__(self) -> None:
        """Create a version attribute."""
        super().__init__(
            partition_key=False,
            sort_key=False,
            default=None,  # Will be set to 1 on first save
            required=False,
        )

    def serialize(self, value: int | None) -> int | None:
        """Convert version to number.

        Args:
            value: Version number.

        Returns:
            The version as int.
        """
        return value

    def deserialize(self, value: Any) -> int | None:
        """Convert number to version.

        Args:
            value: Number from DynamoDB.

        Returns:
            Version as int.
        """
        if value is None:
            return None
        return int(value)
