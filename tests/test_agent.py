import pytest
from unittest.mock import MagicMock, patch
from agent.nodes import check_escalation, lookup_customer, lookup_order

def test_escalation_triggers():
    # Test high risk phrase trigger
    state_risky = {
        "user_message": "I was charged twice on my credit card! This is fraud!",
        "intent": "COMPLAINT",
        "confidence": 0.95,
        "user_id": "CUST001",
        "customer_data": {"customer_id": "CUST001"}
    }
    res_risky = check_escalation(state_risky)
    assert res_risky["requires_human"] is True

    # Test normal inquiry non-escalated
    state_normal = {
        "user_message": "What is your return policy?",
        "intent": "FAQ",
        "confidence": 0.98,
        "user_id": "CUST001",
        "customer_data": {"customer_id": "CUST001"}
    }
    res_normal = check_escalation(state_normal)
    assert res_normal["requires_human"] is False

def test_customer_and_order_nodes():
    state = {
        "user_id": "CUST001",
        "user_message": "Check my order ORD1001",
        "intent": "ORDER"
    }
    cust_res = lookup_customer(state)
    assert cust_res["customer_data"].get("customer_id") == "CUST001"

    order_res = lookup_order(state)
    assert order_res["order_data"].get("order_id") == "ORD1001"
