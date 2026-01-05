# ruff: noqa: F821
# Query active users over 30
users = User.status_index.query(
    status="active",
    filter_condition=User.age >= 30,
)
