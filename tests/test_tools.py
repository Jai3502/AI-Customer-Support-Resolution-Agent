import pytest
from tools.customer_lookup import get_customer
from tools.order_lookup import get_order, get_customer_orders
from tools.ticket import create_ticket, get_all_tickets
from tools.advanced_tools import (
    calculate_refund_and_fees,
    live_policy_search,
    diagnose_product_issue,
    check_inventory_and_restock,
    generate_shipping_label,
)

def test_customer_lookup():
    cust = get_customer("CUST001")
    assert cust is not None
    assert cust.get("customer_id") == "CUST001"

def test_order_lookup():
    order = get_order("ORD1001")
    assert order is not None
    assert order.get("order_id") == "ORD1001"

def test_ticket_creation():
    res = create_ticket(
        customer_id="CUST001",
        description="Test ticket issue",
        priority="High",
        category="Technical"
    )
    assert res.get("ticket_id").startswith("TKT-")

def test_advanced_refund_calculator():
    # Valid recent order refund check
    refund_res = calculate_refund_and_fees("ORD1001", return_reason="Defective item", item_condition="Unopened")
    assert "eligible" in refund_res
    if refund_res["eligible"]:
        assert "instant_voucher_code" in refund_res

def test_live_policy_search():
    res = live_policy_search("What is your refund policy?")
    assert "matched_policies" in res
    assert len(res["matched_policies"]) > 0

def test_product_issue_diagnostics():
    diag = diagnose_product_issue("Electronics", "Battery not charging")
    assert "recommended_troubleshooting" in diag
    assert len(diag["recommended_troubleshooting"]) > 0

def test_inventory_check_and_shipping_label():
    inv = check_inventory_and_restock("Wireless Noise-Canceling Headphones")
    assert "item" in inv
    assert inv["item"]["status"] == "In Stock"

    label = generate_shipping_label("ORD1001", return_reason="Changed mind")
    assert "return_tracking_number" in label
    assert label["label_status"] == "GENERATED & READY FOR PRINTING"
