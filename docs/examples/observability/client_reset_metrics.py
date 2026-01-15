from pydynox import DynamoDBClient

client = DynamoDBClient()


def handle_request(user_id: str) -> dict:
    # Reset at start of each request
    client.reset_metrics()

    # Do operations
    item = client.get_item("users", {"pk": user_id})
    if item:
        client.put_item("logs", {"pk": f"LOG#{user_id}", "action": "viewed"})

    # Check total for this request
    total = client.get_total_metrics()
    print(f"Request used {total.total_rcu} RCU, {total.total_wcu} WCU")

    return item or {}
