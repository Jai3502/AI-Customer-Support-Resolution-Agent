import json
from pathlib import Path
from tools.ticket import get_all_tickets
from tools.customer_lookup import list_all_customers
from tools.order_lookup import list_all_orders


def get_analytics_summary() -> dict:
    """Calculates comprehensive KPIs and metric summaries for support dashboard."""
    tickets = get_all_tickets()
    customers = list_all_customers()
    orders = list_all_orders()

    # --- Ticket Metrics ---
    total_tickets = len(tickets)
    open_tickets = sum(1 for t in tickets if t.get("status") == "Open")
    in_progress_tickets = sum(1 for t in tickets if t.get("status") == "In Progress")
    resolved_tickets = sum(1 for t in tickets if t.get("status") in ["Resolved", "Closed"])

    resolution_rate = round((resolved_tickets / total_tickets * 100), 1) if total_tickets > 0 else 100.0

    tickets_by_priority = {}
    tickets_by_category = {}
    tickets_by_status = {"Open": 0, "In Progress": 0, "Resolved": 0, "Closed": 0}

    for t in tickets:
        p = t.get("priority", "Medium")
        c = t.get("category", "General")
        s = t.get("status", "Open")

        tickets_by_priority[p] = tickets_by_priority.get(p, 0) + 1
        tickets_by_category[c] = tickets_by_category.get(c, 0) + 1
        tickets_by_status[s] = tickets_by_status.get(s, 0) + 1

    # --- Customer Metrics ---
    total_customers = len(customers)
    membership_counts = {}
    city_counts = {}

    for c in customers.values():
        m = c.get("membership", "Standard")
        city = c.get("city", "Unknown")
        membership_counts[m] = membership_counts.get(m, 0) + 1
        city_counts[city] = city_counts.get(city, 0) + 1

    # --- Order Metrics ---
    total_orders = len(orders)
    total_revenue = sum(o.get("amount", 0) for o in orders.values() if o.get("payment_status") == "Paid")

    orders_by_status = {}
    orders_by_category = {}
    revenue_by_category = {}
    payment_methods = {}

    for o in orders.values():
        st = o.get("order_status", "Unknown")
        cat = o.get("category", "General")
        amt = o.get("amount", 0)
        pm = o.get("payment_method", "Other")

        orders_by_status[st] = orders_by_status.get(st, 0) + 1
        orders_by_category[cat] = orders_by_category.get(cat, 0) + 1
        revenue_by_category[cat] = revenue_by_category.get(cat, 0) + (amt if o.get("payment_status") == "Paid" else 0)
        payment_methods[pm] = payment_methods.get(pm, 0) + 1

    return {
        "kpis": {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate": resolution_rate,
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
        },
        "tickets": {
            "by_status": tickets_by_status,
            "by_priority": tickets_by_priority,
            "by_category": tickets_by_category,
        },
        "customers": {
            "by_membership": membership_counts,
            "by_city": city_counts,
        },
        "orders": {
            "by_status": orders_by_status,
            "by_category": orders_by_category,
            "revenue_by_category": revenue_by_category,
            "by_payment_method": payment_methods,
        }
    }
