# ruff: noqa: F821
# Query active users with pk starting with "USER#"
users = User.status_index.query(
    status="active",
    range_key_condition=User.pk.begins_with("USER#"),
)

# Query with comparison
users = User.status_index.query(
    status="active",
    range_key_condition=User.pk >= "USER#100",
)
