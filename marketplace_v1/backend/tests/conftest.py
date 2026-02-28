from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.models import Permission, Role, User
from app.security.password import hash_password


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "test-secret"


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        seed_roles_permissions()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app) -> User:
    with app.app_context():
        admin_role = db.session.query(Role).filter_by(name="admin").one()
        user = User(email="admin@example.com", password_hash=hash_password("Admin123!"), is_active=True)
        user.roles.append(admin_role)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


def seed_roles_permissions() -> None:
    permission_codes = [
        "order.read",
        "order.create",
        "order.update",
        "order.status.update",
        "user.read",
        "user.role.update",
        "audit.read",
        "inventory.read",
        "inventory.update",
        "admin.manage",
        "buyer.group.read",
        "buyer.group.manage",
        "seller.validate",
        "product.read",
        "product.manage",
    ]

    permissions = {code: Permission(code=code) for code in permission_codes}
    db.session.add_all(list(permissions.values()))

    roles = {
        "admin": Role(name="admin"),
        "seller": Role(name="seller"),
        "buyer": Role(name="buyer"),
        "support_ops": Role(name="support_ops"),
        "super_admin": Role(name="super_admin"),
        "ambassador": Role(name="ambassador"),
    }

    roles["admin"].permissions.extend(list(permissions.values()))
    roles["seller"].permissions.extend(
        [
            permissions["order.read"],
            permissions["order.create"],
            permissions["order.update"],
            permissions["order.status.update"],
        ]
    )
    roles["buyer"].permissions.extend([permissions["order.read"], permissions["order.create"]])
    roles["support_ops"].permissions.extend(
        [
            permissions["order.read"],
            permissions["order.status.update"],
            permissions["audit.read"],
            permissions["user.read"],
        ]
    )
    roles["super_admin"].permissions.extend(list(permissions.values()))
    roles["ambassador"].permissions.extend([permissions["buyer.group.read"]])

    db.session.add_all(list(roles.values()))
    db.session.commit()
