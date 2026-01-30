"""Test fixtures for example tests.

Contains table schemas and test data used by run_all_examples.py.
"""

from __future__ import annotations

import time

from pydynox import DynamoDBClient

# Table schemas: name -> (partition_key, sort_key or None)
TABLE_SCHEMAS = {
    # Tables with pk + sk
    "users": ("pk", "sk"),
    "posts": ("pk", "sk"),
    "orders": ("pk", "sk"),
    "analytics": ("pk", "sk"),
    "api_usage": ("pk", "sk"),
    # Tables with pk only
    "products": ("pk", None),
    "events": ("pk", None),
    "sessions": ("pk", None),
    "documents": ("pk", None),
    "counters": ("pk", None),
    "configs": ("pk", None),
    "articles": ("pk", None),
    "items": ("pk", None),
    "accounts": ("pk", None),
    "carts": ("pk", None),
    "temp": ("pk", None),
    "sensitive_data": ("pk", None),
    "compressed_data": ("pk", None),
}


def create_tables(client: DynamoDBClient) -> None:
    """Create all test tables."""
    for name, (partition_key, sort_key) in TABLE_SCHEMAS.items():
        if client.sync_table_exists(name):
            continue
        client.sync_create_table(
            name,
            partition_key=(partition_key, "S"),
            sort_key=(sort_key, "S") if sort_key else None,
            wait=True,
        )


def populate_data(client: DynamoDBClient) -> None:
    """Populate tables with test data."""
    now = int(time.time())

    def insert(table: str, items: list[dict]) -> None:
        for item in items:
            client.put_item(table, item)

    insert(
        "users",
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25, "status": "active"},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30, "status": "active"},
            {"pk": "USER#3", "sk": "PROFILE", "name": "Charlie", "age": 17, "status": "inactive"},
            {"pk": "USER#4", "sk": "PROFILE", "name": "Diana", "age": 22, "status": "active"},
            {"pk": "USER#5", "sk": "PROFILE", "name": "Eve", "age": 35, "status": "inactive"},
        ],
    )

    insert(
        "posts",
        [
            {"pk": "USER#1", "sk": "POST#1", "title": "First", "content": "Hello", "likes": 10},
            {"pk": "USER#1", "sk": "POST#2", "title": "Second", "content": "World", "likes": 5},
            {"pk": "USER#2", "sk": "POST#1", "title": "Bob's", "content": "Hi", "likes": 20},
        ],
    )

    insert(
        "orders",
        [
            {
                "pk": f"ORDER#{i}",
                "sk": "DETAILS",
                "user_id": f"USER#{i % 3}",
                "amount": 100 + i * 10,
            }
            for i in range(1, 11)
        ],
    )

    insert(
        "products",
        [
            {"pk": "PRODUCT#1", "name": "Laptop", "price": 1000, "stock": 5},
            {"pk": "PRODUCT#2", "name": "Mouse", "price": 25, "stock": 100},
            {"pk": "PRODUCT#3", "name": "Keyboard", "price": 75, "stock": 50},
        ],
    )

    insert(
        "events",
        [
            {"pk": "EVENT#1", "name": "Event 1", "ttl": now + 3600},
            {"pk": "EVENT#2", "name": "Event 2", "ttl": now + 7200},
        ],
    )

    insert(
        "sessions",
        [
            {"pk": "SESSION#1", "user_id": "USER#1", "expires_at": now + 3600},
            {"pk": "SESSION#2", "user_id": "USER#2", "expires_at": now + 7200},
        ],
    )

    insert(
        "documents",
        [
            {"pk": "DOC#1", "title": "Document 1", "content": "Content 1", "version": 1},
            {"pk": "DOC#2", "title": "Document 2", "content": "Content 2", "version": 1},
        ],
    )

    insert("counters", [{"pk": "COUNTER#1", "value": 0, "version": 1}])
    insert("analytics", [{"pk": "/home", "sk": "2024-01-15", "views": 0}])
    insert("configs", [{"pk": "CONFIG#1", "settings": {"theme": "dark", "lang": "en"}}])
    insert(
        "articles",
        [{"pk": "ARTICLE#1", "title": "Article 1", "created_at": "2024-01-15T10:00:00Z"}],
    )
    insert("items", [{"pk": "ITEM#1", "name": "Item 1"}])
    insert("accounts", [{"pk": "ACCOUNT#1", "balance": 1000}, {"pk": "ACCOUNT#2", "balance": 500}])
    insert("carts", [{"pk": "CART#1", "items": [], "total": 0}])
    insert("api_usage", [{"pk": "API#1", "sk": "2024-01-15", "count": 0}])
    insert("temp", [{"pk": "TEMP#1", "data": "temporary"}])

    insert(
        "sensitive_data",
        [
            {"pk": "DATA#1", "name": "Alice", "email": "alice@example.com"},
            {"pk": "DATA#2", "name": "Bob", "email": "bob@example.com"},
        ],
    )

    insert(
        "compressed_data",
        [
            {"pk": "DATA#1", "name": "Alice", "description": "A" * 1000},
            {"pk": "DATA#2", "name": "Bob", "description": "B" * 1000},
        ],
    )
