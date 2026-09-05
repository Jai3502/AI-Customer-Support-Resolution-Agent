import json
from pathlib import Path

ORDER_FILE = Path("data/orders.json")


def get_order(order_id: str) -> dict:
    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Unable to load order database: {e}"}

    order = data.get(order_id)

    if not order:
        return {"error": f"Order {order_id} was not found."}

    return order


def get_customer_orders(customer_id: str) -> list[dict]:
    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return []

    customer_orders = [
        order for order in data.values()
        if order.get("customer_id") == customer_id
    ]

    # Sort most recent first
    customer_orders.sort(key=lambda x: x.get("order_date", ""), reverse=True)
    return customer_orders