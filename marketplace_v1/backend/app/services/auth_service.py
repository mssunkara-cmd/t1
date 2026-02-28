from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import AmbassadorBuyerAssignment, Role, User
from app.security.password import hash_password, verify_password


def find_user_by_email(email: str) -> User | None:
    stmt = (
        select(User)
        .where(User.email == email.lower().strip())
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    return db.session.execute(stmt).scalar_one_or_none()


def find_user_by_id(user_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    return db.session.execute(stmt).scalar_one_or_none()


def authenticate_user(email: str, password: str) -> User | None:
    user = find_user_by_email(email)
    if not user or not user.is_active:
        return None

    if not verify_password(user.password_hash, password):
        return None

    return user


def any_users_exist() -> bool:
    return db.session.scalar(select(User.id).limit(1)) is not None


def find_role_by_name(name: str) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    return db.session.execute(stmt).scalar_one_or_none()


def create_user(
    email: str,
    password: str,
    roles: list[Role] | None = None,
    profile: dict[str, str | None] | None = None,
    seller_status: str | None = None,
    source_region_id: int | None = None,
    major_distribution_region_id: int | None = None,
    assigned_admin_user_id: int | None = None,
) -> User:
    normalized_email = email.lower().strip()
    profile_data = profile or {}
    user = User(
        email=normalized_email,
        first_name=profile_data.get("first_name"),
        last_name=profile_data.get("last_name"),
        address_line1=profile_data.get("address_line1"),
        address_line2=profile_data.get("address_line2"),
        address_line3=profile_data.get("address_line3"),
        zip_code=profile_data.get("zip_code"),
        phone_number=profile_data.get("phone_number"),
        region=profile_data.get("region"),
        source_region_id=source_region_id,
        major_distribution_region_id=major_distribution_region_id,
        assigned_admin_user_id=assigned_admin_user_id,
        seller_status=seller_status,
        password_hash=hash_password(password),
        is_active=True,
    )
    if roles:
        user.roles.extend(roles)

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise

    db.session.refresh(user)
    return user


def assign_roles_to_user(user: User, roles: list[Role]) -> User:
    user.roles = roles
    db.session.commit()
    db.session.refresh(user)
    return user


def list_users() -> list[User]:
    stmt = select(User).options(selectinload(User.roles))
    return list(db.session.execute(stmt).scalars().all())


def update_user_profile(user: User, updates: dict[str, str | None]) -> User:
    for field, value in updates.items():
        setattr(user, field, value)
    db.session.commit()
    db.session.refresh(user)
    return user


def update_seller_status(user: User, seller_status: str) -> User:
    user.seller_status = seller_status
    db.session.commit()
    db.session.refresh(user)
    return user


def update_seller_assigned_admin(user: User, assigned_admin_user_id: int | None) -> User:
    user.assigned_admin_user_id = assigned_admin_user_id
    db.session.commit()
    db.session.refresh(user)
    return user


def assign_buyer_to_ambassador(ambassador_user_id: int, buyer_user_id: int) -> None:
    existing = db.session.scalar(
        select(AmbassadorBuyerAssignment).where(
            AmbassadorBuyerAssignment.ambassador_user_id == ambassador_user_id,
            AmbassadorBuyerAssignment.buyer_user_id == buyer_user_id,
        )
    )
    if existing is not None:
        return

    db.session.add(
        AmbassadorBuyerAssignment(
            ambassador_user_id=ambassador_user_id,
            buyer_user_id=buyer_user_id,
        )
    )
    db.session.commit()


def remove_buyer_from_ambassador(ambassador_user_id: int, buyer_user_id: int) -> bool:
    assignment = db.session.scalar(
        select(AmbassadorBuyerAssignment).where(
            AmbassadorBuyerAssignment.ambassador_user_id == ambassador_user_id,
            AmbassadorBuyerAssignment.buyer_user_id == buyer_user_id,
        )
    )
    if assignment is None:
        return False

    db.session.delete(assignment)
    db.session.commit()
    return True


def list_buyers_for_ambassador(ambassador_user_id: int) -> list[User]:
    stmt = (
        select(User)
        .join(
            AmbassadorBuyerAssignment,
            AmbassadorBuyerAssignment.buyer_user_id == User.id,
        )
        .where(AmbassadorBuyerAssignment.ambassador_user_id == ambassador_user_id)
    )
    return list(db.session.execute(stmt).scalars().all())


def build_auth_claims(user: User) -> dict[str, list[str]]:
    roles = sorted({role.name for role in user.roles})
    permissions = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    return {"roles": roles, "permissions": permissions}
