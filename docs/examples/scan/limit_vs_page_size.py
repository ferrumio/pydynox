from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# limit = total items to return (stops after N items)
# page_size = items per DynamoDB request (controls pagination)

# Example 1: Get exactly 50 items total
# DynamoDB will fetch 50 items per request, stop after 50 total
users = list(User.scan(limit=50))
print(f"Got {len(users)} users")  # Always 50 (or less if table has fewer)


# Example 2: Get all items, but fetch 100 per page
# DynamoDB will fetch 100 items per request, return all items
for user in User.scan(page_size=100):
    print(f"User: {user.name}")


# Example 3: Get 500 items total, fetching 100 per page
# DynamoDB will make 5 requests (100 * 5 = 500)
users = list(
    User.scan(
        limit=500,
        page_size=100,
    )
)
print(f"Got {len(users)} users")  # 500 items


# Example 4: Scan with filter and pagination
# Note: filter is applied AFTER DynamoDB reads items
# So page_size controls how many items DynamoDB reads per request,
# not how many items pass the filter
active_users = list(
    User.scan(
        filter_condition=User.age >= 18,
        limit=100,
        page_size=50,
    )
)
print(f"Got {len(active_users)} adult users")


# Example 5: Manual pagination for "load more" UI
result = User.scan(limit=20, page_size=20)
first_page = list(result)
print(f"First page: {len(first_page)} items")

if result.last_evaluated_key:
    result = User.scan(
        limit=20,
        page_size=20,
        last_evaluated_key=result.last_evaluated_key,
    )
    second_page = list(result)
    print(f"Second page: {len(second_page)} items")
