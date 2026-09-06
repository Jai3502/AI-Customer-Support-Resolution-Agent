import json
import hashlib
from pathlib import Path
from datetime import datetime

USERS_FILE = Path("data/users.json")
CUSTOMERS_FILE = Path("data/customers.json")

# ---------------------------------------------------------------------------
# RBAC Permissions Matrix
# ---------------------------------------------------------------------------
PERM_CHAT_SUPPORT = "chat_support"
PERM_VIEW_ADMIN_DESK = "view_admin_desk"
PERM_MANAGE_TICKETS = "manage_tickets"
PERM_DELETE_TICKETS = "delete_tickets"
PERM_EDIT_CUSTOMERS = "edit_customers"
PERM_UPDATE_ORDERS = "update_orders"
PERM_VIEW_ANALYTICS = "view_analytics"
PERM_VIEW_PERFORMANCE = "view_performance"
PERM_MANAGE_ROLES = "manage_roles"

ROLE_PERMISSIONS = {
    "admin": [
        PERM_CHAT_SUPPORT,
        PERM_VIEW_ADMIN_DESK,
        PERM_MANAGE_TICKETS,
        PERM_DELETE_TICKETS,
        PERM_EDIT_CUSTOMERS,
        PERM_UPDATE_ORDERS,
        PERM_VIEW_ANALYTICS,
        PERM_VIEW_PERFORMANCE,
        PERM_MANAGE_ROLES,
    ],
    "agent": [
        PERM_CHAT_SUPPORT,
        PERM_VIEW_ADMIN_DESK,
        PERM_MANAGE_TICKETS,
        PERM_EDIT_CUSTOMERS,
        PERM_UPDATE_ORDERS,
    ],
    "auditor": [
        PERM_CHAT_SUPPORT,
        PERM_VIEW_ANALYTICS,
        PERM_VIEW_PERFORMANCE,
    ],
    "customer": [
        PERM_CHAT_SUPPORT,
    ],
}


def _hash_password(password: str, salt: str = "ai_support_salt_2026") -> str:
    """Hash password using SHA-256 with salt."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def seed_default_users_if_needed():
    """Seed initial user accounts including Admin, Agent, Auditor, and Customers."""
    if USERS_FILE.exists():
        return

    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    default_users = {
        "admin": {
            "username": "admin",
            "password_hash": _hash_password("admin123"),
            "role": "admin",
            "name": "System Administrator",
            "email": "admin@supportagent.com",
            "customer_id": None,
            "created_at": datetime.now().isoformat(),
        },
        "agent1": {
            "username": "agent1",
            "password_hash": _hash_password("agent123"),
            "role": "agent",
            "name": "Sarah Connor (Support Lead)",
            "email": "sarah.connor@supportagent.com",
            "customer_id": None,
            "created_at": datetime.now().isoformat(),
        },
        "auditor1": {
            "username": "auditor1",
            "password_hash": _hash_password("auditor123"),
            "role": "auditor",
            "name": "Michael Chang (Auditor)",
            "email": "michael.chang@supportagent.com",
            "customer_id": None,
            "created_at": datetime.now().isoformat(),
        },
        "rahul": {
            "username": "rahul",
            "password_hash": _hash_password("customer123"),
            "role": "customer",
            "name": "Rahul Sharma",
            "email": "rahul.sharma@example.com",
            "customer_id": "CUST001",
            "created_at": datetime.now().isoformat(),
        },
        "priya": {
            "username": "priya",
            "password_hash": _hash_password("customer123"),
            "role": "customer",
            "name": "Priya Verma",
            "email": "priya.verma@example.com",
            "customer_id": "CUST002",
            "created_at": datetime.now().isoformat(),
        },
        "amit": {
            "username": "amit",
            "password_hash": _hash_password("customer123"),
            "role": "customer",
            "name": "Amit Patel",
            "email": "amit.patel@example.com",
            "customer_id": "CUST003",
            "created_at": datetime.now().isoformat(),
        },
        "sneha": {
            "username": "sneha",
            "password_hash": _hash_password("customer123"),
            "role": "customer",
            "name": "Sneha Iyer",
            "email": "sneha.iyer@example.com",
            "customer_id": "CUST004",
            "created_at": datetime.now().isoformat(),
        },
        "vikram": {
            "username": "vikram",
            "password_hash": _hash_password("customer123"),
            "role": "customer",
            "name": "Vikram Singh",
            "email": "vikram.singh@example.com",
            "customer_id": "CUST005",
            "created_at": datetime.now().isoformat(),
        },
    }

    USERS_FILE.write_text(json.dumps(default_users, indent=4), encoding="utf-8")


def load_users() -> dict:
    seed_default_users_if_needed()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=4), encoding="utf-8")


def authenticate_user(username_or_email: str, password: str) -> dict | None:
    users = load_users()
    identifier = username_or_email.strip().lower()
    hashed = _hash_password(password)

    for user_data in users.values():
        if (user_data.get("username").lower() == identifier or
                user_data.get("email").lower() == identifier):
            if user_data.get("password_hash") == hashed:
                return user_data
    return None


def has_permission(role: str, permission: str) -> bool:
    """Check if a user role possesses a specific permission."""
    if not role:
        return False
    permissions = ROLE_PERMISSIONS.get(role.lower(), [])
    return permission in permissions


def update_user_role(username: str, new_role: str) -> bool:
    """Update role for a user (Admin restricted)."""
    users = load_users()
    username_clean = username.strip().lower()

    if username_clean in users and new_role in ROLE_PERMISSIONS:
        users[username_clean]["role"] = new_role
        save_users(users)
        return True
    return False


def register_customer(username: str, email: str, name: str, password: str, city: str = "Bengaluru") -> tuple[bool, str, dict | None]:
    users = load_users()
    username_clean = username.strip().lower()
    email_clean = email.strip().lower()

    if not username_clean or not password or not name:
        return False, "Username, name, and password are required.", None

    for user in users.values():
        if user.get("username").lower() == username_clean:
            return False, f"Username '{username}' is already taken.", None
        if user.get("email").lower() == email_clean:
            return False, f"Email '{email}' is already registered.", None

    existing_cust_ids = [u.get("customer_id") for u in users.values() if u.get("customer_id")]
    cust_num = len(existing_cust_ids) + 1
    new_cust_id = f"CUST{cust_num:03d}"

    new_user = {
        "username": username_clean,
        "password_hash": _hash_password(password),
        "role": "customer",
        "name": name.strip(),
        "email": email_clean,
        "customer_id": new_cust_id,
        "created_at": datetime.now().isoformat(),
    }

    users[username_clean] = new_user
    save_users(users)

    try:
        customers = json.loads(CUSTOMERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        customers = {}

    customers[new_cust_id] = {
        "customer_id": new_cust_id,
        "name": name.strip(),
        "email": email_clean,
        "phone": "+91-99000" + str(cust_num).zfill(5),
        "preferred_language": "English",
        "membership": "Standard",
        "city": city,
        "state": "India",
        "pincode": "560001",
        "total_orders": 0,
        "notes": "Registered via web application."
    }
    CUSTOMERS_FILE.write_text(json.dumps(customers, indent=4), encoding="utf-8")

    return True, "Account created successfully!", new_user
