from tools.ticket import create_ticket


def escalate_to_human(
    customer_id: str,
    reason: str,
    priority: str = "High",
) -> dict:
    ticket = create_ticket(
        customer_id=customer_id,
        category="Human Escalation",
        description=reason,
        priority=priority,
    )

    return {"escalated": True, "ticket": ticket}