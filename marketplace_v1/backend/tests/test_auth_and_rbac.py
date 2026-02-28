from __future__ import annotations

from app.extensions import db
from app.models import Role, User


def _bootstrap_admin(client):
    return client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": "admin1@example.com", "password": "Admin123!"},
    )


def test_bootstrap_admin_only_once(client):
    first = _bootstrap_admin(client)
    assert first.status_code == 201

    second = _bootstrap_admin(client)
    assert second.status_code == 409


def test_register_and_login(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "buyer1@example.com", "password": "Buyer123!", "role": "buyer"},
    )
    assert register_response.status_code == 201
    register_data = register_response.get_json()
    assert register_data["user"]["email"] == "buyer1@example.com"
    assert "buyer" in register_data["user"]["roles"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer1@example.com", "password": "Buyer123!"},
    )
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data


def test_orders_endpoint_requires_order_read_permission(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "seller1@example.com", "password": "Seller123!", "role": "seller"},
    )
    token = register_response.get_json()["access_token"]

    response = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_admin_role_assignment_requires_permission(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "buyer2@example.com", "password": "Buyer123!", "role": "buyer"},
    )
    buyer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer2@example.com", "password": "Buyer123!"},
    )
    buyer_token = buyer_login.get_json()["access_token"]

    with client.application.app_context():
        target_user = db.session.query(User).filter_by(email="buyer2@example.com").one()

    forbidden_response = client.post(
        f"/api/v1/admin/users/{target_user.id}/roles",
        json={"roles": ["seller"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_can_assign_roles(client):
    _bootstrap_admin(client)

    client.post(
        "/api/v1/auth/register",
        json={"email": "user3@example.com", "password": "User123!", "role": "buyer"},
    )

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin1@example.com", "password": "Admin123!"},
    )
    admin_token = admin_login.get_json()["access_token"]

    with client.application.app_context():
        user = db.session.query(User).filter_by(email="user3@example.com").one()

    assign_response = client.post(
        f"/api/v1/admin/users/{user.id}/roles",
        json={"roles": ["seller", "support_ops"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 200
    payload = assign_response.get_json()
    assert payload["roles"] == ["seller", "support_ops"]

    with client.application.app_context():
        refreshed_user = db.session.get(User, user.id)
        role_names = sorted(role.name for role in refreshed_user.roles)
        assert role_names == ["seller", "support_ops"]


def test_register_rejects_invalid_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "X123456!", "role": "admin"},
    )
    assert response.status_code == 400


def test_admin_users_requires_permission(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "buyer4@example.com", "password": "Buyer123!", "role": "buyer"},
    )
    token = register.get_json()["access_token"]

    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_users_success_with_admin_token(client):
    _bootstrap_admin(client)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin1@example.com", "password": "Admin123!"},
    )
    token = login.get_json()["access_token"]

    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["items"], list)
    assert any(item["email"] == "admin1@example.com" for item in data["items"])
