"""Model base class with ORM-style CRUD operations."""

from typing import Any, ClassVar, Optional, Type, TypeVar

from .attributes import Attribute
from .client import DynamoDBClient

M = TypeVar("M", bound="Model")


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> "ModelMeta":
        # Collect attributes from parent classes
        attributes: dict[str, Attribute] = {}
        hash_key: Optional[str] = None
        range_key: Optional[str] = None

        for base in bases:
            if hasattr(base, "_attributes"):
                attributes.update(base._attributes)
            if hasattr(base, "_hash_key") and base._hash_key:
                hash_key = base._hash_key
            if hasattr(base, "_range_key") and base._range_key:
                range_key = base._range_key

        # Collect attributes from this class
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Attribute):
                attr_value.attr_name = attr_name
                attributes[attr_name] = attr_value

                if attr_value.hash_key:
                    hash_key = attr_name
                if attr_value.range_key:
                    range_key = attr_name

        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # Store metadata
        cls._attributes = attributes
        cls._hash_key = hash_key
        cls._range_key = range_key

        return cls


class Model(metaclass=ModelMeta):
    """Base class for DynamoDB models with ORM-style CRUD.

    Define your model by subclassing and adding attributes:

    Example:
        >>> from pydynox import Model, StringAttribute, NumberAttribute
        >>>
        >>> class User(Model):
        ...     class Meta:
        ...         table = "users"
        ...         region = "us-east-1"
        ...
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
        >>>
        >>> # Create and save
        >>> user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
        >>> user.save()
        >>>
        >>> # Get by key
        >>> user = User.get(pk="USER#123", sk="PROFILE")
        >>> print(user.name)
        >>>
        >>> # Update
        >>> user.name = "Jane"
        >>> user.save()
        >>>
        >>> # Delete
        >>> user.delete()
    """

    _attributes: ClassVar[dict[str, Attribute]]
    _hash_key: ClassVar[Optional[str]]
    _range_key: ClassVar[Optional[str]]
    _client: ClassVar[Optional[DynamoDBClient]] = None

    class Meta:
        """Model configuration.

        Attributes:
            table: DynamoDB table name (required).
            region: AWS region (optional, uses default if not set).
            endpoint_url: Custom endpoint (optional, for local testing).
        """

        table: str
        region: Optional[str] = None
        endpoint_url: Optional[str] = None

    def __init__(self, **kwargs: Any):
        """Create a model instance.

        Args:
            **kwargs: Attribute values.
        """
        for attr_name, attr in self._attributes.items():
            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif attr.default is not None:
                setattr(self, attr_name, attr.default)
            elif not attr.null:
                raise ValueError(f"Attribute '{attr_name}' is required")
            else:
                setattr(self, attr_name, None)

    @classmethod
    def _get_client(cls) -> DynamoDBClient:
        """Get or create the DynamoDB client."""
        if cls._client is None:
            meta = cls.Meta
            cls._client = DynamoDBClient(
                region=getattr(meta, "region", None),
                endpoint_url=getattr(meta, "endpoint_url", None),
            )
        return cls._client

    @classmethod
    def _get_table(cls) -> str:
        """Get the table name from Meta."""
        if not hasattr(cls.Meta, "table"):
            raise ValueError(f"Model {cls.__name__} must define Meta.table")
        return cls.Meta.table

    @classmethod
    def get(cls: Type[M], **keys: Any) -> Optional[M]:
        """Get an item from DynamoDB by its key.

        Args:
            **keys: The key attributes (hash_key and optional range_key).

        Returns:
            The model instance if found, None otherwise.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> if user:
            ...     print(user.name)
        """
        client = cls._get_client()
        table = cls._get_table()

        item = client.get_item(table, keys)
        if item is None:
            return None

        return cls.from_dict(item)

    def save(self, condition: Optional[str] = None) -> None:
        """Save the model to DynamoDB.

        Creates a new item or replaces an existing one.

        Args:
            condition: Optional condition expression.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> user.save()
        """
        client = self._get_client()
        table = self._get_table()
        item = self.to_dict()

        # TODO: Add condition expression support when put_item supports it
        client.put_item(table, item)

    def delete(self, condition: Optional[str] = None) -> None:
        """Delete the model from DynamoDB.

        Args:
            condition: Optional condition expression.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.delete()
        """
        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # TODO: Add condition expression support
        client.delete_item(table, key)

    def update(self, **kwargs: Any) -> None:
        """Update specific attributes on the model.

        Updates both the local instance and DynamoDB.

        Args:
            **kwargs: Attribute values to update.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.update(name="Jane", age=31)
        """
        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # Update local instance
        for attr_name, value in kwargs.items():
            if attr_name not in self._attributes:
                raise ValueError(f"Unknown attribute: {attr_name}")
            setattr(self, attr_name, value)

        # Update in DynamoDB
        client.update_item(table, key, updates=kwargs)

    def _get_key(self) -> dict[str, Any]:
        """Get the key dict for this instance."""
        key = {}
        if self._hash_key:
            key[self._hash_key] = getattr(self, self._hash_key)
        if self._range_key:
            key[self._range_key] = getattr(self, self._range_key)
        return key

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dict.

        Returns:
            Dict with all attribute values.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> user.to_dict()
            {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
        """
        result = {}
        for attr_name in self._attributes:
            value = getattr(self, attr_name, None)
            if value is not None:
                result[attr_name] = value
        return result

    @classmethod
    def from_dict(cls: Type[M], data: dict[str, Any]) -> M:
        """Create a model instance from a dict.

        Args:
            data: Dict with attribute values.

        Returns:
            A new model instance.

        Example:
            >>> data = {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
            >>> user = User.from_dict(data)
        """
        return cls(**data)

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on key attributes."""
        if not isinstance(other, self.__class__):
            return False
        return self._get_key() == other._get_key()
