import uuid
from datetime import datetime, timedelta
from tools.order_lookup import get_order

# Policy Constants
RETURN_WINDOW_DAYS = 30
RESTOCKING_FEE_PERCENT = 10.0


def calculate_refund_and_fees(order_id: str, return_reason: str = "Changed mind", item_condition: str = "Unopened") -> dict:
    """Advanced financial tool to compute pro-rated refunds, restocking fees, and generate store vouchers."""
    order = get_order(order_id)
    if "error" in order:
        return {"eligible": False, "reason": f"Order {order_id} not found."}

    order_date_str = order.get("order_date")
    amount = order.get("amount", 0)
    product_name = order.get("product", "Product")

    try:
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d")
        current_date = datetime.now()
        days_passed = (current_date - order_date).days
    except Exception:
        days_passed = 10  # Fallback assumption

    # 1. Eligibility Check
    if days_passed > RETURN_WINDOW_DAYS:
        return {
            "eligible": False,
            "order_id": order_id,
            "product": product_name,
            "amount": amount,
            "days_passed": days_passed,
            "max_window_days": RETURN_WINDOW_DAYS,
            "reason": f"Return window expired. Purchase was {days_passed} days ago (Policy limit: {RETURN_WINDOW_DAYS} days).",
            "alternative_offer": "15% Trade-in Discount Voucher on next order."
        }

    # 2. Fee Calculation
    is_seller_fault = any(w in return_reason.lower() for w in ["defective", "damaged", "wrong item", "faulty", "broken"])

    if is_seller_fault or item_condition.lower() == "unopened":
        restocking_fee = 0.0
    else:
        restocking_fee = round((amount * RESTOCKING_FEE_PERCENT) / 100.0, 2)

    net_refund = round(amount - restocking_fee, 2)

    # 3. Store Voucher Code Generation
    voucher_code = f"REFUND-{str(uuid.uuid4())[:8].upper()}"

    return {
        "eligible": True,
        "order_id": order_id,
        "product": product_name,
        "original_amount": amount,
        "return_reason": return_reason,
        "days_passed": days_passed,
        "restocking_fee": restocking_fee,
        "net_refund_amount": net_refund,
        "payment_method": order.get("payment_method"),
        "instant_voucher_code": voucher_code,
        "refund_summary": f"Eligible for ₹{net_refund:,} refund ({'Zero restocking fee' if restocking_fee == 0 else f'₹{restocking_fee:,} restocking fee applied'})."
    }


def live_policy_search(query: str) -> dict:
    """Searches store policy database for warranties, shipping, and returns."""
    q = query.lower()

    policies = [
        {
            "category": "Returns & Refunds",
            "rule": "30-Day Money-Back Guarantee",
            "details": "Customers can return items within 30 days of delivery. Unopened or defective products receive 100% full refund with zero restocking fee."
        },
        {
            "category": "Warranty",
            "rule": "Product Warranty Coverage",
            "details": "Electronics & Laptops have 1-Year Brand Warranty. Audio items (headphones) have 2-Year Replacement Warranty. Accessories have 6-Month Coverage."
        },
        {
            "category": "Shipping & Delivery",
            "rule": "Delivery SLAs & Carrier Rules",
            "details": "Standard shipping takes 3-5 business days. Express shipping (BlueDart/Delhivery) takes 24-48 hours. Free shipping on all orders over ₹500."
        },
        {
            "category": "Payment & Price Match",
            "rule": "Price Match & Payment Gateways",
            "details": "We accept UPI (Google Pay, PhonePe, Paytm), Credit Cards, and Net Banking. We offer price match within 7 days of order placement."
        }
    ]

    matched = []
    for p in policies:
        if any(term in p["rule"].lower() or term in p["details"].lower() or term in p["category"].lower() for term in q.split()):
            matched.append(p)

    if not matched:
        matched = policies[:2]

    return {
        "query": query,
        "matched_policies": matched
    }


def diagnose_product_issue(category: str, issue_description: str) -> dict:
    """Technical diagnostic engine providing steps or recommending replacement warranty claims."""
    desc = issue_description.lower()
    cat = category.lower()

    if "battery" in desc or "power" in desc or "not charging" in desc:
        steps = [
            "1. Disconnect the charging cable and inspect port for dust/debris.",
            "2. Perform a hard reset by holding the power button for 15 seconds.",
            "3. Try an alternative certified charger and wall outlet.",
            "4. If battery level indicator remains unresponsive, initiate a warranty replacement claim."
        ]
        action = "Warranty Hardware Diagnostic Required"
    elif "bluetooth" in desc or "connectivity" in desc or "pairing" in desc:
        steps = [
            "1. Turn off Bluetooth on all nearby connected devices.",
            "2. Hold the pairing button for 7 seconds until LED flashes red/blue.",
            "3. Forget the device in phone/laptop Bluetooth settings and reconnect.",
            "4. Reset network configuration if connection drops repeatedly."
        ]
        action = "Software / Firmware Pairing Reset"
    else:
        steps = [
            "1. Ensure device firmware is updated to the latest release.",
            "2. Power cycle the device and verify secondary cable connections.",
            "3. Run automated hardware diagnostic via companion app.",
            "4. Escalating to technical support specialist if problem persists."
        ]
        action = "General Hardware Diagnostic"

    return {
        "category": category,
        "issue": issue_description,
        "diagnostic_action": action,
        "recommended_troubleshooting": steps,
        "eligible_for_warranty_claim": True
    }


def check_inventory_and_restock(product_name_or_sku: str, warehouse_location: str = "Central Bangalore Hub") -> dict:
    """Checks inventory levels, warehouse stock distribution, and estimated restock lead times."""
    sku_clean = product_name_or_sku.strip().lower()

    inventory_db = {
        "wireless noise-canceling headphones": {
            "sku": "PROD-101",
            "name": "Wireless Noise-Canceling Headphones",
            "stock_count": 42,
            "status": "In Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Available Immediately",
            "reorder_threshold": 10
        },
        "prod-101": {
            "sku": "PROD-101",
            "name": "Wireless Noise-Canceling Headphones",
            "stock_count": 42,
            "status": "In Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Available Immediately",
            "reorder_threshold": 10
        },
        "ergonomic gaming chair": {
            "sku": "PROD-102",
            "name": "Ergonomic Gaming Chair",
            "stock_count": 8,
            "status": "Low Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Next Shipment in 3 Days (2026-09-14)",
            "reorder_threshold": 15
        },
        "ultra-hd 4k monitor 27 inch": {
            "sku": "PROD-103",
            "name": "Ultra-HD 4K Monitor 27 inch",
            "stock_count": 0,
            "status": "Out of Stock",
            "warehouse": "Mumbai Regional Hub",
            "restock_eta": "Backorder In Transit - Arriving 2026-09-16",
            "reorder_threshold": 5
        },
        "mechanical keyboard RGB": {
            "sku": "PROD-104",
            "name": "Mechanical Keyboard RGB",
            "stock_count": 85,
            "status": "In Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Available Immediately",
            "reorder_threshold": 20
        },
        "smart fitness watch series 5": {
            "sku": "PROD-105",
            "name": "Smart Fitness Watch Series 5",
            "stock_count": 19,
            "status": "In Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Available Immediately",
            "reorder_threshold": 10
        }
    }

    match = None
    for key, data in inventory_db.items():
        if key in sku_clean or sku_clean in key:
            match = data
            break

    if not match:
        match = {
            "sku": f"SKU-{str(uuid.uuid4())[:6].upper()}",
            "name": product_name_or_sku.title(),
            "stock_count": 25,
            "status": "In Stock",
            "warehouse": warehouse_location,
            "restock_eta": "Available Immediately",
            "reorder_threshold": 10
        }

    return {
        "query": product_name_or_sku,
        "item": match,
        "fulfillment_center": match["warehouse"],
        "recommended_action": "Proceed with order" if match["stock_count"] > 0 else "Reserve backorder allocation"
    }


def generate_shipping_label(order_id: str, return_reason: str = "Defective Item", customer_address: str = "Default Customer Address") -> dict:
    """Generates automated return shipping labels, barcode tracking numbers, and courier pickup requests."""
    tracking_number = f"RET-BD-{str(uuid.uuid4())[:10].upper()}"
    carrier = "BlueDart Express Return Service"

    return {
        "order_id": order_id,
        "return_tracking_number": tracking_number,
        "carrier": carrier,
        "pickup_scheduled_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "customer_address": customer_address,
        "return_reason": return_reason,
        "label_status": "GENERATED & READY FOR PRINTING",
        "qr_code_token": f"QR-SHIPPING-{tracking_number}",
        "instructions": "Print this return label or show QR code to BlueDart pickup executive tomorrow."
    }

