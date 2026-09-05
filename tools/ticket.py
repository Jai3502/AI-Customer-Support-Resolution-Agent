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
        "created_at": datetime.now().isoformat(),
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