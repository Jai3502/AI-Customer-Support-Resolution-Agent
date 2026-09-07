import json
from pathlib import Path
from database.pg_client import is_postgres_available, get_db_session
from database.schema import CustomerModel

CUSTOMER_FILE = Path("data/customers.json")


def get_customer(customer_id: str) -> dict:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                c = session.query(CustomerModel).filter_by(customer_id=customer_id).first()
                if c:
                    return {
                        "customer_id": c.customer_id,
                        "name": c.name,
                        "email": c.email,
                        "phone": c.phone,
                        "preferred_language": c.preferred_language or "English",
                        "membership": c.membership or "Standard",
                        "city": c.city,
                        "state": c.state,
                        "pincode": c.pincode,
                        "total_orders": c.total_orders or 0,
                        "notes": c.notes or ""
                    }
            except Exception:
                pass
            finally:
                session.close()

    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Unable to load customer database: {e}"}

    customer = data.get(customer_id)

    if not customer:
        return {"error": f"Customer {customer_id} was not found."}

    return customer


def list_all_customers() -> dict:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_customers = session.query(CustomerModel).all()
                if db_customers:
                    res = {}
                    for c in db_customers:
                        res[c.customer_id] = {
                            "customer_id": c.customer_id,
                            "name": c.name,
                            "email": c.email,
                            "phone": c.phone,
                            "preferred_language": c.preferred_language or "English",
                            "membership": c.membership or "Standard",
                            "city": c.city,
                            "state": c.state,
                            "pincode": c.pincode,
                            "total_orders": c.total_orders or 0,
                            "notes": c.notes or ""
                        }
                    return res
            except Exception:
                pass
            finally:
                session.close()

    try:
        return json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_customer_notes(customer_id: str, notes: str) -> dict | None:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                c = session.query(CustomerModel).filter_by(customer_id=customer_id).first()
                if c:
                    c.notes = notes
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

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
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                c = session.query(CustomerModel).filter_by(customer_id=customer_id).first()
                if c:
                    c.membership = membership
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if customer_id not in data:
        return None

    data[customer_id]["membership"] = membership
    CUSTOMER_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return data[customer_id]