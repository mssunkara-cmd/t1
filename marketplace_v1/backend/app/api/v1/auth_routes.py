from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError

from app.services.auth_service import (
    assign_buyer_to_ambassador,
    any_users_exist,
    authenticate_user,
    build_auth_claims,
    create_user,
    find_role_by_name,
    find_user_by_id,
    update_user_profile,
)
from app.extensions import db
from app.models import Region, RegionDefault


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/bootstrap-admin")
def bootstrap_admin() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    profile, profile_error = _extract_profile(payload)

    if not email or not password:
        return {"message": "email and password are required"}, 400
    if profile_error:
        return {"message": profile_error}, 400

    if any_users_exist():
        return {"message": "bootstrap already completed"}, 409

    admin_role = find_role_by_name("admin")
    if admin_role is None:
        return {"message": "admin role not found; run migrations"}, 500
    super_admin_role = find_role_by_name("super_admin")
    bootstrap_roles = [admin_role]
    if super_admin_role is not None:
        bootstrap_roles.append(super_admin_role)

    try:
        user = create_user(email=email, password=password, roles=bootstrap_roles, profile=profile)
    except IntegrityError:
        return {"message": "email already exists"}, 409

    claims = build_auth_claims(user)
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _build_user_response(user, claims["roles"]),
    }, 201


@auth_bp.post("/register")
def register() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role_name = str(payload.get("role", "buyer")).strip().lower()
    source_region_id_raw = payload.get("source_region_id")
    major_distribution_region_id_raw = payload.get("major_distribution_region_id")
    profile, profile_error = _extract_profile(payload)

    if not email or not password:
        return {"message": "email and password are required"}, 400
    if profile_error:
        return {"message": profile_error}, 400

    if role_name not in {"buyer", "seller"}:
        return {"message": "role must be either buyer or seller"}, 400

    role = find_role_by_name(role_name)
    if role is None:
        return {"message": "role not found; run migrations"}, 500

    seller_status = "pending_validation" if role_name == "seller" else None
    source_region_id = None
    major_distribution_region_id = None
    assigned_admin_user_id = None
    if role_name == "seller":
        if not isinstance(source_region_id_raw, int):
            return {"message": "source_region_id is required for seller registration"}, 400
        source_region = db.session.get(Region, source_region_id_raw)
        if source_region is None:
            return {"message": "source region not found"}, 400
        if source_region.region_type != "source":
            return {"message": "selected region is not a source region"}, 400
        source_region_id = source_region_id_raw
        region_default = db.session.query(RegionDefault).filter_by(region_id=source_region_id).one_or_none()
        if region_default is None or region_default.default_admin_user_id is None:
            return {
                "message": "no default admin configured for selected source region; contact super_admin"
            }, 400
        assigned_admin_user_id = region_default.default_admin_user_id
    else:
        if not isinstance(major_distribution_region_id_raw, int):
            return {"message": "major_distribution_region_id is required for buyer registration"}, 400
        major_distribution_region = db.session.get(Region, major_distribution_region_id_raw)
        if major_distribution_region is None:
            return {"message": "major distribution region not found"}, 400
        if (
            major_distribution_region.region_type != "distribution"
            or major_distribution_region.distribution_level != "major"
        ):
            return {"message": "selected region is not a major distribution region"}, 400
        major_distribution_region_id = major_distribution_region_id_raw

    try:
        user = create_user(
            email=email,
            password=password,
            roles=[role],
            profile=profile,
            seller_status=seller_status,
            source_region_id=source_region_id,
            major_distribution_region_id=major_distribution_region_id,
            assigned_admin_user_id=assigned_admin_user_id,
        )
    except IntegrityError:
        return {"message": "email already exists"}, 409

    if role_name == "buyer" and major_distribution_region_id is not None:
        region_default = (
            db.session.query(RegionDefault)
            .filter_by(region_id=major_distribution_region_id)
            .one_or_none()
        )
        if (
            region_default is not None
            and region_default.default_ambassador_user_id is not None
        ):
            assign_buyer_to_ambassador(region_default.default_ambassador_user_id, user.id)

    claims = build_auth_claims(user)
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _build_user_response(user, claims["roles"]),
    }, 201


@auth_bp.post("/login")
def login() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not email or not password:
        return {"message": "email and password are required"}, 400

    user = authenticate_user(email, password)
    if user is None:
        return {"message": "invalid credentials"}, 401

    claims = build_auth_claims(user)
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _build_user_response(user, claims["roles"]),
    }, 200


@auth_bp.get("/source-regions")
def list_source_regions() -> tuple[dict[str, list[dict[str, object]]], int]:
    regions = (
        db.session.query(Region)
        .filter(Region.region_type == "source")
        .order_by(Region.region_name.asc())
        .all()
    )
    return {
        "items": [
            {
                "region_id": region.region_id,
                "region_name": region.region_name,
                "region_description": region.region_description,
                "region_type": region.region_type,
            }
            for region in regions
        ]
    }, 200


@auth_bp.get("/major-distribution-regions")
def list_major_distribution_regions() -> tuple[dict[str, list[dict[str, object]]], int]:
    regions = (
        db.session.query(Region)
        .filter(Region.region_type == "distribution", Region.distribution_level == "major")
        .order_by(Region.region_name.asc())
        .all()
    )
    return {
        "items": [
            {
                "region_id": region.region_id,
                "region_name": region.region_name,
                "region_description": region.region_description,
                "region_type": region.region_type,
                "distribution_level": region.distribution_level,
                "parent_region_id": region.parent_region_id,
            }
            for region in regions
        ]
    }, 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh() -> tuple[dict[str, str], int]:
    identity = _current_user_id_from_token()
    if identity is None:
        return {"message": "invalid token identity"}, 401
    user = find_user_by_id(identity)
    if user is None or not user.is_active:
        return {"message": "user not found or inactive"}, 401

    claims = build_auth_claims(user)
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    return {"access_token": access_token}, 200


@auth_bp.get("/me")
@jwt_required()
def me() -> tuple[dict[str, object], int]:
    identity = _current_user_id_from_token()
    if identity is None:
        return {"message": "invalid token identity"}, 401
    user = find_user_by_id(identity)
    if user is None:
        return {"message": "user not found"}, 404

    claims = build_auth_claims(user)
    return _build_user_response(user, claims["roles"]), 200


@auth_bp.patch("/me")
@jwt_required()
def update_me() -> tuple[dict[str, object], int]:
    identity = _current_user_id_from_token()
    if identity is None:
        return {"message": "invalid token identity"}, 401
    user = find_user_by_id(identity)
    if user is None:
        return {"message": "user not found"}, 404

    payload = request.get_json(silent=True) or {}
    updates, error = _extract_profile_updates(payload)
    if error:
        return {"message": error}, 400
    if not updates:
        return {"message": "no profile fields provided"}, 400

    updated_user = update_user_profile(user, updates)
    claims = build_auth_claims(updated_user)
    return _build_user_response(updated_user, claims["roles"]), 200


def _current_user_id_from_token() -> int | None:
    raw_identity = get_jwt_identity()
    try:
        return int(raw_identity)
    except (TypeError, ValueError):
        return None


def _build_user_response(user, roles: list[str]) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "roles": roles,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "address_line1": user.address_line1,
        "address_line2": user.address_line2,
        "address_line3": user.address_line3,
        "zip_code": user.zip_code,
        "phone_number": user.phone_number,
        "region": user.region,
        "source_region_id": user.source_region_id,
        "major_distribution_region_id": user.major_distribution_region_id,
        "assigned_admin_user_id": user.assigned_admin_user_id,
        "seller_status": user.seller_status,
    }


def _extract_profile(payload: dict[str, object]) -> tuple[dict[str, str | None], str | None]:
    limits = {
        "first_name": 250,
        "last_name": 250,
        "address_line1": 100,
        "address_line2": 100,
        "address_line3": 100,
        "zip_code": 6,
        "phone_number": 12,
        "region": 100,
    }
    profile: dict[str, str | None] = {}
    for field_name, max_len in limits.items():
        raw_value = payload.get(field_name)
        if raw_value is None:
            profile[field_name] = None
            continue

        value = str(raw_value).strip()
        if len(value) > max_len:
            return {}, f"{field_name} exceeds max length {max_len}"
        profile[field_name] = value or None

    return profile, None


def _extract_profile_updates(payload: dict[str, object]) -> tuple[dict[str, str | None], str | None]:
    limits = {
        "first_name": 250,
        "last_name": 250,
        "address_line1": 100,
        "address_line2": 100,
        "address_line3": 100,
        "zip_code": 6,
        "phone_number": 12,
        "region": 100,
    }
    updates: dict[str, str | None] = {}
    for field_name, max_len in limits.items():
        if field_name not in payload:
            continue
        raw_value = payload.get(field_name)
        if raw_value is None:
            updates[field_name] = None
            continue
        value = str(raw_value).strip()
        if len(value) > max_len:
            return {}, f"{field_name} exceeds max length {max_len}"
        updates[field_name] = value or None
    return updates, None
