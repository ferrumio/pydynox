# ruff: noqa: F821
# Query by email
users = User.email_index.query(email="john@example.com")
for user in users:
    print(user.name)

# Query by status
active_users = User.status_index.query(status="active")
for user in active_users:
    print(user.email)
