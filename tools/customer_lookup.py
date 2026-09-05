import json
from pathlib import Path

CUSTOMER_FILE = Path("data/customers.json")


def get_customer(customer_id: str) -> dict:
    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Unable to load customer database: {e}"}

    customer = data.get(customer_id)

    if not customer:
        return {"error": f"Customer {customer_id} was not found."}

    return customer


def list_all_customers() -> dict:
    try:
        return json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {}