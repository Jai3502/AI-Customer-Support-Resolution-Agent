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
    except Exception:
        return {}


def update_customer_notes(customer_id: str, notes: str) -> dict | None:
    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if customer_id not in data:
        return None

    data[customer_id]["notes"] = notes
    CUSTOMER_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return data[customer_id]


def update_customer_membership(customer_id: str, membership: str) -> dict | None:
    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if customer_id not in data:
        return None

    data[customer_id]["membership"] = membership
    CUSTOMER_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return data[customer_id]