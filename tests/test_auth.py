import pytest
from auth import (
    authenticate_user,
    has_permission,
    _hash_password,
    register_customer,
    update_user_role,
    PERM_CHAT_SUPPORT,
    PERM_VIEW_ADMIN_DESK,
    PERM_MANAGE_ROLES,
)

def test_password_hashing():
    hashed1 = _hash_password("admin123")
    hashed2 = _hash_password("admin123")
    hashed3 = _hash_password("different_pass")

    assert hashed1 == hashed2
    assert hashed1 != hashed3

def test_rbac_permissions():
    assert has_permission("admin", PERM_CHAT_SUPPORT) is True
    assert has_permission("admin", PERM_VIEW_ADMIN_DESK) is True
    assert has_permission("admin", PERM_MANAGE_ROLES) is True

    assert has_permission("customer", PERM_CHAT_SUPPORT) is True
    assert has_permission("customer", PERM_VIEW_ADMIN_DESK) is False
    assert has_permission("customer", PERM_MANAGE_ROLES) is False

    assert has_permission("auditor", PERM_CHAT_SUPPORT) is True
    assert has_permission("auditor", PERM_VIEW_ADMIN_DESK) is False

def test_user_authentication():
    # Test valid admin login
    user = authenticate_user("admin", "admin123")
    assert user is not None
    assert user["username"] == "admin"
    assert user["role"] == "admin"

    # Test invalid password
    invalid_user = authenticate_user("admin", "wrongpassword")
    assert invalid_user is None

def test_customer_registration_and_role_update():
    import uuid
    uid = str(uuid.uuid4())[:8]
    uname = f"pytest_user_{uid}"
    uemail = f"pytest_{uid}@example.com"

    # Register test user
    success, msg, user_data = register_customer(
        username=uname,
        email=uemail,
        name="Pytest User",
        password="testpassword123",
        city="Mumbai"
    )
    assert success is True
    assert user_data["role"] == "customer"

    # Upgrade role to agent
    role_success = update_user_role(uname, "agent")
    assert role_success is True

    # Re-authenticate and verify new role
    updated_user = authenticate_user(uname, "testpassword123")
    assert updated_user["role"] == "agent"
