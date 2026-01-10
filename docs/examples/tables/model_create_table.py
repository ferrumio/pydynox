"""Example: Create table from Model schema."""

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

# Setup client
client = DynamoDBClient()
set_default_client(client)


class User(Model):
    """User model with GSI for email lookup."""

    model_config = ModelConfig(table="example_model_users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()

    # GSI for querying by email
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )


# Create table from model schema (includes hash key, range key, and GSIs)
if not User.table_exists():
    User.create_table(wait=True)

# Verify table exists
assert User.table_exists()

# Save and query to verify GSI works
user = User(pk="USER#1", sk="PROFILE", email="test@example.com", status="active", age=30)
user.save()

# Query by GSI
results = list(User.email_index.query(email="test@example.com"))
assert len(results) == 1
assert results[0].pk == "USER#1"

# Cleanup
User.delete_table()
