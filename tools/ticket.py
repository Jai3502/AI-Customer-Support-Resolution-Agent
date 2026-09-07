import json
import uuid
from pathlib import Path
from datetime import datetime
from database.pg_client import is_postgres_available, get_db_session
from database.schema import TicketModel

TICKET_FILE = Path("data/tickets.json")


def _ticket_model_to_dict(t: TicketModel) -> dict:
    return {
        "ticket_id": t.ticket_id,
        "customer_id": t.customer_id,
        "category": t.category,
        "description": t.description,
        "priority": t.priority or "Medium",
        "status": t.status or "Open",
        "assigned_agent": t.assigned_agent or "Unassigned",
        "resolution_notes": t.resolution_notes or "",
        "created_at": t.created_at,
        "updated_at": t.created_at
    }


def create_ticket(
    customer_id: str,
    category: str,
    description: str,
    priority: str = "Medium",
) -> dict:
    ticket_id = "TKT-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now().isoformat()

    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "category": category,
        "description": description,
        "priority": priority,
        "status": "Open",
        "assigned_agent": "Unassigned",
        "resolution_notes": "",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                session.add(TicketModel(
                    ticket_id=ticket_id,
                    customer_id=customer_id,
                    category=category,
                    description=description,
                    priority=priority,
                    status="Open",
                    assigned_agent="Unassigned",
                    resolution_notes=""
                ))
                session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
    except Exception:
        tickets = []

    tickets.append(ticket)
    TICKET_FILE.write_text(json.dumps(tickets, indent=4), encoding="utf-8")

    return ticket


def get_customer_tickets(customer_id: str) -> list[dict]:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_tickets = session.query(TicketModel).filter_by(customer_id=customer_id).all()
                if db_tickets:
                    return [_ticket_model_to_dict(t) for t in db_tickets]
            except Exception:
                pass
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        return [t for t in tickets if t.get("customer_id") == customer_id]
    except Exception:
        return []


def get_all_tickets() -> list[dict]:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_tickets = session.query(TicketModel).all()
                if db_tickets:
                    return [_ticket_model_to_dict(t) for t in db_tickets]
            except Exception:
                pass
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        for t in tickets:
            if "assigned_agent" not in t:
                t["assigned_agent"] = "Unassigned"
            if "resolution_notes" not in t:
                t["resolution_notes"] = ""
            if "updated_at" not in t:
                t["updated_at"] = t.get("created_at", datetime.now().isoformat())
        return tickets
    except Exception:
        return []


def update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: str = "",
    agent_name: str = "Admin",
) -> dict | None:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                t = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
                if t:
                    t.status = status
                    if resolution_notes:
                        t.resolution_notes = resolution_notes
                    t.assigned_agent = agent_name
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    updated_ticket = None
    for t in tickets:
        if t.get("ticket_id") == ticket_id:
            t["status"] = status
            if resolution_notes:
                t["resolution_notes"] = resolution_notes
            t["assigned_agent"] = agent_name
            t["updated_at"] = datetime.now().isoformat()
            updated_ticket = t
            break

    if updated_ticket:
        TICKET_FILE.write_text(json.dumps(tickets, indent=4), encoding="utf-8")

    return updated_ticket


def update_ticket_priority(ticket_id: str, priority: str) -> dict | None:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                t = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
                if t:
                    t.priority = priority
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    updated_ticket = None
    for t in tickets:
        if t.get("ticket_id") == ticket_id:
            t["priority"] = priority
            t["updated_at"] = datetime.now().isoformat()
            updated_ticket = t
            break

    if updated_ticket:
        TICKET_FILE.write_text(json.dumps(tickets, indent=4), encoding="utf-8")

    return updated_ticket


def delete_ticket(ticket_id: str) -> bool:
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                t = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
                if t:
                    session.delete(t)
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()

    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        filtered = [t for t in tickets if t.get("ticket_id") != ticket_id]
        if len(filtered) < len(tickets):
            TICKET_FILE.write_text(json.dumps(filtered, indent=4), encoding="utf-8")
            return True
    except Exception:
        pass
    return False