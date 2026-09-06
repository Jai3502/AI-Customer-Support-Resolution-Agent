import json
import uuid
from pathlib import Path
from datetime import datetime

TICKET_FILE = Path("data/tickets.json")


def create_ticket(
    customer_id: str,
    category: str,
    description: str,
    priority: str = "Medium",
) -> dict:
    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
    except Exception:
        tickets = []

    ticket_id = "TKT-" + str(uuid.uuid4())[:8].upper()

    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "category": category,
        "description": description,
        "priority": priority,
        "status": "Open",
        "assigned_agent": "Unassigned",
        "resolution_notes": "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    tickets.append(ticket)
    TICKET_FILE.write_text(json.dumps(tickets, indent=4), encoding="utf-8")

    return ticket


def get_customer_tickets(customer_id: str) -> list[dict]:
    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        return [t for t in tickets if t.get("customer_id") == customer_id]
    except Exception:
        return []


def get_all_tickets() -> list[dict]:
    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        # Ensure older tickets have assigned_agent & resolution_notes fields
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
    try:
        tickets = json.loads(TICKET_FILE.read_text(encoding="utf-8"))
        filtered = [t for t in tickets if t.get("ticket_id") != ticket_id]
        if len(filtered) < len(tickets):
            TICKET_FILE.write_text(json.dumps(filtered, indent=4), encoding="utf-8")
            return True
    except Exception:
        pass
    return False