import json
from pathlib import Path
from database.pg_client import is_postgres_available, get_db_session
from database.schema import OrderModel

ORDER_FILE = Path("data/orders.json")


def _order_model_to_dict(o: OrderModel) -> dict:
    return {
        "order_id": o.order_id,
        "customer_id": o.customer_id,
        "product": o.product,
        "category": o.category,
        "amount": o.amount,
        "payment_status": o.payment_status,
        "payment_method": o.payment_method,
        "order_status": o.order_status,
        "carrier": o.carrier,
        "tracking_id": o.tracking_id,
        "order_date": o.order_date,
        "estimated_delivery": o.estimated_delivery
    }


def get_order(order_id: str) -> dict:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                o = session.query(OrderModel).filter_by(order_id=order_id).first()
                if o:
                    return _order_model_to_dict(o)
            except Exception:
                pass
            finally:
                session.close()

    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Unable to load order database: {e}"}

    order = data.get(order_id)

    if not order:
        return {"error": f"Order {order_id} was not found."}

    return order


def get_customer_orders(customer_id: str) -> list[dict]:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_orders = session.query(OrderModel).filter_by(customer_id=customer_id).order_by(OrderModel.order_date.desc()).all()
                if db_orders:
                    return [_order_model_to_dict(o) for o in db_orders]
            except Exception:
                pass
            finally:
                session.close()

    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

    customer_orders = [
        order for order in data.values()
        if order.get("customer_id") == customer_id
    ]

    # Sort most recent first
    customer_orders.sort(key=lambda x: x.get("order_date", ""), reverse=True)
    return customer_orders


def list_all_orders() -> dict:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_orders = session.query(OrderModel).all()
                if db_orders:
                    return {o.order_id: _order_model_to_dict(o) for o in db_orders}
            except Exception:
                pass
            finally:
                session.close()

    try:
        return json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_order_status(order_id: str, status: str, carrier: str = None, tracking_id: str = None) -> dict | None:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                o = session.query(OrderModel).filter_by(order_id=order_id).first()
                if o:
                    o.order_status = status
                    if carrier:
                        o.carrier = carrier
                    if tracking_id:
                        o.tracking_id = tracking_id
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if order_id not in data:
        return None

    order = data[order_id]
    order["order_status"] = status
    if carrier:
        order["carrier"] = carrier
    if tracking_id:
        order["tracking_id"] = tracking_id

    ORDER_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return order