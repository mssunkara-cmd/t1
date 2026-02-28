from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import and_, or_
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    AmbassadorBuyerAssignment,
    FreshProduceInventoryItem,
    InventoryItem,
    ProcurementOrder,
    ProcurementOrderReview,
    ProcurementOrderReviewImage,
    Product,
    ProductType,
    Region,
    RegionDefault,
    Supplier,
    SupplierProduct,
    User,
)
from app.security.decorators import require_permissions
from app.services.auth_service import (
    assign_roles_to_user,
    assign_buyer_to_ambassador,
    find_role_by_name,
    find_user_by_id,
    list_buyers_for_ambassador,
    list_users,
    remove_buyer_from_ambassador,
    update_seller_assigned_admin,
    update_seller_status,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/users")
@require_permissions("user.read")
def get_users() -> tuple[dict[str, list[dict[str, object]]], int]:
    role_filter = request.args.get("role")
    page = _int_query_arg("page", 1, minimum=1)
    page_size = _int_query_arg("page_size", 20, minimum=1, maximum=100)

    users = list_users()
    if role_filter:
        normalized_role = role_filter.strip().lower()
        users = [u for u in users if any(r.name == normalized_role for r in u.roles)]

    total = len(users)
    start = (page - 1) * page_size
    end = start + page_size
    page_users = users[start:end]

    return {
        "items": [
            {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "roles": sorted(role.name for role in user.roles),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "region": user.region,
                "source_region_id": user.source_region_id,
                "major_distribution_region_id": user.major_distribution_region_id,
                "seller_status": user.seller_status,
                "assigned_admin_user_id": user.assigned_admin_user_id,
            }
            for user in page_users
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }, 200


@admin_bp.post("/users/<int:user_id>/roles")
@require_permissions("user.role.update")
def update_user_roles(user_id: int) -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    role_names = payload.get("roles")

    if not isinstance(role_names, list) or not role_names:
        return {"message": "roles must be a non-empty list"}, 400

    normalized = sorted({str(role).strip().lower() for role in role_names if str(role).strip()})
    roles = []
    missing_roles = []
    for role_name in normalized:
        role = find_role_by_name(role_name)
        if role is None:
            missing_roles.append(role_name)
        else:
            roles.append(role)

    if missing_roles:
        return {"message": "unknown roles", "roles": missing_roles}, 400

    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    updated_user = assign_roles_to_user(user, roles)
    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "roles": sorted(role.name for role in updated_user.roles),
    }, 200


@admin_bp.get("/inventory")
@jwt_required()
def list_inventory() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()

    if "super_admin" not in roles and "admin" not in roles and "seller" not in roles:
        return {"message": "Forbidden"}, 403

    page = _int_query_arg("page", 1, minimum=1)
    page_size = _int_query_arg("page_size", 20, minimum=1, maximum=100)
    seller_id = _optional_int_query_arg("seller_id")
    product_id = _optional_int_query_arg("product_id")
    product_type = (request.args.get("product_type") or "").strip()
    status = request.args.get("status")

    def _filtered_query(model_cls: type[InventoryItem] | type[FreshProduceInventoryItem]):
        query = db.session.query(model_cls)
        if "seller" in roles and "admin" not in roles and "super_admin" not in roles:
            query = query.filter(model_cls.seller_id == current_user_id)
        if seller_id is not None:
            query = query.filter(model_cls.seller_id == seller_id)
        if product_id is not None:
            query = query.filter(model_cls.product_id == product_id)
        if product_type:
            query = query.join(Product, model_cls.product_id == Product.id).filter(Product.product_type == product_type)
        if status:
            query = query.outerjoin(User, model_cls.seller_id == User.id).outerjoin(
                Supplier, model_cls.supplier_id == Supplier.supplier_id
            )
            if status in {"active", "inactive"}:
                query = query.filter(
                    and_(
                        model_cls.origin_type == "procurement",
                        Supplier.is_active.is_(status == "active"),
                    )
                )
            else:
                query = query.filter(
                    and_(
                        model_cls.origin_type == "seller_direct",
                        User.seller_status == status,
                    )
                )
        return query

    regular_items = _filtered_query(InventoryItem).all()
    fresh_items = _filtered_query(FreshProduceInventoryItem).all()

    combined_items: list[tuple[str, InventoryItem | FreshProduceInventoryItem]] = [
        ("regular", item) for item in regular_items
    ] + [("fresh_produce", item) for item in fresh_items]
    combined_items.sort(
        key=lambda row: (
            row[1].entry_date or datetime.min.replace(tzinfo=timezone.utc),
            row[1].id,
        ),
        reverse=True,
    )

    total = len(combined_items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = combined_items[start:end]
    return {
        "items": [
            _build_inventory_item_response(item, inventory_kind=kind)
            for kind, item in page_items
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }, 200


@admin_bp.post("/inventory")
@jwt_required()
def create_inventory_item() -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()
    if "admin" not in roles and "super_admin" not in roles and "seller" not in roles:
        return {"message": "Forbidden"}, 403

    payload = request.get_json(silent=True) or {}
    product_id = payload.get("product_id")
    seller_id = payload.get("seller_id")
    quantity = payload.get("quantity")

    if not isinstance(product_id, int):
        return {"message": "product_id must be integer"}, 400
    if not isinstance(quantity, int) or quantity < 0:
        return {"message": "quantity must be a non-negative integer"}, 400

    product = db.session.get(Product, product_id)
    if product is None:
        return {"message": "product not found"}, 404

    if "seller" in roles and "admin" not in roles and "super_admin" not in roles:
        seller_id = current_user_id
    else:
        if not isinstance(seller_id, int):
            return {"message": "seller_id must be integer"}, 400
        seller = db.session.get(User, seller_id)
        if seller is None:
            return {"message": "seller not found"}, 404
        seller_roles = {r.name for r in seller.roles}
        if "seller" not in seller_roles:
            return {"message": "seller_id is not a seller user"}, 400

        if "super_admin" not in roles:
            if seller.seller_status != "valid":
                return {"message": "seller must be valid"}, 400
            if not _seller_is_in_admin_source_regions(current_user_id, seller):
                return {"message": "seller is not in admin source regions"}, 400

    is_fresh_produce = product.product_type.strip().lower() == "fresh_produce"
    if is_fresh_produce:
        item = FreshProduceInventoryItem(
            product_id=product_id,
            seller_id=seller_id,
            supplier_id=None,
            origin_type="seller_direct",
            origin="seller_direct",
            entry_date=datetime.now(timezone.utc),
            estimated_quantity=quantity,
            created_by_admin_user_id=current_user_id,
        )
        inventory_kind = "fresh_produce"
    else:
        item = InventoryItem(
            product_id=product_id,
            seller_id=seller_id,
            supplier_id=None,
            origin_type="seller_direct",
            origin="seller_direct",
            entry_date=datetime.now(timezone.utc),
            quantity=quantity,
            created_by_admin_user_id=current_user_id,
        )
        inventory_kind = "regular"
    db.session.add(item)
    db.session.commit()
    db.session.refresh(item)

    return {
        **_build_inventory_item_response(item, inventory_kind=inventory_kind),
    }, 201


@admin_bp.put("/inventory/<int:item_id>")
@jwt_required()
def update_inventory_item(item_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()
    if "admin" not in roles and "super_admin" not in roles and "seller" not in roles:
        return {"message": "Forbidden"}, 403

    inventory_kind = str(request.args.get("inventory_kind", "regular")).strip().lower()
    if inventory_kind not in {"regular", "fresh_produce"}:
        return {"message": "inventory_kind must be regular or fresh_produce"}, 400
    model_cls = InventoryItem if inventory_kind == "regular" else FreshProduceInventoryItem

    item = db.session.get(model_cls, item_id)
    if item is None:
        return {"message": "inventory item not found"}, 404
    if "seller" in roles and "admin" not in roles and "super_admin" not in roles:
        if item.seller_id != current_user_id or item.origin_type != "seller_direct":
            return {"message": "you can only edit your own seller inventory entries"}, 403
    elif "super_admin" not in roles and item.created_by_admin_user_id != current_user_id:
        return {"message": "you can only edit your own inventory entries"}, 403

    payload = request.get_json(silent=True) or {}
    quantity = payload.get("quantity")
    if not isinstance(quantity, int) or quantity < 0:
        return {"message": "quantity must be a non-negative integer"}, 400

    if inventory_kind == "regular":
        item.quantity = quantity
    else:
        item.estimated_quantity = quantity
    db.session.commit()
    db.session.refresh(item)
    return {
        **_build_inventory_item_response(item, inventory_kind=inventory_kind),
    }, 200


@admin_bp.delete("/inventory/<int:item_id>")
@jwt_required()
def delete_inventory_item(item_id: int) -> tuple[dict[str, str], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()
    if "admin" not in roles and "super_admin" not in roles and "seller" not in roles:
        return {"message": "Forbidden"}, 403

    inventory_kind = str(request.args.get("inventory_kind", "regular")).strip().lower()
    if inventory_kind not in {"regular", "fresh_produce"}:
        return {"message": "inventory_kind must be regular or fresh_produce"}, 400
    model_cls = InventoryItem if inventory_kind == "regular" else FreshProduceInventoryItem

    item = db.session.get(model_cls, item_id)
    if item is None:
        return {"message": "inventory item not found"}, 404
    if "seller" in roles and "admin" not in roles and "super_admin" not in roles:
        if item.seller_id != current_user_id or item.origin_type != "seller_direct":
            return {"message": "you can only delete your own seller inventory entries"}, 403
    elif "super_admin" not in roles and item.created_by_admin_user_id != current_user_id:
        return {"message": "you can only delete your own inventory entries"}, 403

    db.session.delete(item)
    db.session.commit()
    return {"message": "deleted"}, 200


@admin_bp.get("/inventory/product-options")
@jwt_required()
def inventory_product_options() -> tuple[dict[str, list[dict[str, object]]], int]:
    products = db.session.query(Product).order_by(Product.product_name.asc()).all()
    return {
        "items": [
            {
                "id": p.id,
                "product_name": p.product_name,
                "product_type": p.product_type,
                "product_unit": p.product_unit,
                "validity_days": p.validity_days,
            }
            for p in products
        ]
    }, 200


@admin_bp.get("/inventory/seller-options")
@jwt_required()
def inventory_seller_options() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()
    if "admin" not in roles and "super_admin" not in roles:
        return {"message": "Forbidden"}, 403

    query = db.session.query(User).filter(User.roles.any(name="seller"), User.seller_status == "valid")
    if "super_admin" not in roles:
        region_ids = _source_region_ids_for_admin(current_user_id)
        query = query.filter(User.source_region_id.in_(region_ids)) if region_ids else query.filter(False)

    sellers = query.order_by(User.id.asc()).all()
    return {
        "items": [
            {
                "id": s.id,
                "email": s.email,
                "source_region_id": s.source_region_id,
                "seller_status": s.seller_status,
            }
            for s in sellers
        ]
    }, 200


@admin_bp.get("/regions")
@require_permissions("admin.manage")
def list_regions() -> tuple[dict[str, list[dict[str, object]]], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    regions = db.session.query(Region).order_by(Region.region_name.asc()).all()
    defaults = db.session.query(RegionDefault).all()
    regions_by_id = {r.region_id: r for r in regions}
    defaults_by_region_id = {d.region_id: d for d in defaults}
    return {
        "items": [
            {
                "region_id": region.region_id,
                "region_name": region.region_name,
                "region_description": region.region_description,
                "region_type": region.region_type,
                "distribution_level": region.distribution_level,
                "parent_region_id": region.parent_region_id,
                "parent_region_name": regions_by_id.get(region.parent_region_id).region_name
                if region.parent_region_id and regions_by_id.get(region.parent_region_id)
                else None,
                "default_admin_user_id": defaults_by_region_id.get(region.region_id).default_admin_user_id
                if defaults_by_region_id.get(region.region_id)
                else None,
                "default_ambassador_user_id": defaults_by_region_id.get(
                    region.region_id
                ).default_ambassador_user_id
                if defaults_by_region_id.get(region.region_id)
                else None,
            }
            for region in regions
        ]
    }, 200


@admin_bp.post("/regions")
@require_permissions("admin.manage")
def create_region() -> tuple[dict[str, object], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    payload = request.get_json(silent=True) or {}
    region_name = str(payload.get("region_name", "")).strip()
    region_description = str(payload.get("region_description", "")).strip() or None
    region_type = str(payload.get("region_type", "")).strip().lower()
    distribution_level_raw = payload.get("distribution_level")
    distribution_level = (
        str(distribution_level_raw).strip().lower()
        if distribution_level_raw is not None and str(distribution_level_raw).strip()
        else None
    )
    parent_region_id = payload.get("parent_region_id")

    error = _validate_region_fields(region_name, region_description, region_type)
    if error:
        return {"message": error}, 400
    hierarchy_error = _validate_distribution_hierarchy(
        region_type=region_type,
        distribution_level=distribution_level,
        parent_region_id=parent_region_id,
    )
    if hierarchy_error:
        return {"message": hierarchy_error}, 400

    existing = (
        db.session.query(Region)
        .filter(Region.region_name == region_name, Region.region_type == region_type)
        .one_or_none()
    )
    if existing:
        return {"message": "region_name + region_type must be unique"}, 409

    region = Region(
        region_name=region_name,
        region_description=region_description,
        region_type=region_type,
        distribution_level=distribution_level,
        parent_region_id=parent_region_id,
    )
    db.session.add(region)
    db.session.commit()
    db.session.refresh(region)
    return {
        "region_id": region.region_id,
        "region_name": region.region_name,
        "region_description": region.region_description,
        "region_type": region.region_type,
        "distribution_level": region.distribution_level,
        "parent_region_id": region.parent_region_id,
    }, 201


@admin_bp.put("/regions/<int:region_id>")
@require_permissions("admin.manage")
def update_region(region_id: int) -> tuple[dict[str, object], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    region = db.session.get(Region, region_id)
    if region is None:
        return {"message": "region not found"}, 404

    payload = request.get_json(silent=True) or {}
    region_name = str(payload.get("region_name", "")).strip()
    region_description = str(payload.get("region_description", "")).strip() or None
    region_type = str(payload.get("region_type", "")).strip().lower()
    distribution_level_raw = payload.get("distribution_level")
    distribution_level = (
        str(distribution_level_raw).strip().lower()
        if distribution_level_raw is not None and str(distribution_level_raw).strip()
        else None
    )
    parent_region_id = payload.get("parent_region_id")

    error = _validate_region_fields(region_name, region_description, region_type)
    if error:
        return {"message": error}, 400
    if parent_region_id == region_id:
        return {"message": "parent_region_id cannot reference same region"}, 400
    hierarchy_error = _validate_distribution_hierarchy(
        region_type=region_type,
        distribution_level=distribution_level,
        parent_region_id=parent_region_id,
    )
    if hierarchy_error:
        return {"message": hierarchy_error}, 400

    existing = (
        db.session.query(Region)
        .filter(
            Region.region_name == region_name,
            Region.region_type == region_type,
            Region.region_id != region_id,
        )
        .one_or_none()
    )
    if existing:
        return {"message": "region_name + region_type must be unique"}, 409

    region.region_name = region_name
    region.region_description = region_description
    region.region_type = region_type
    region.distribution_level = distribution_level
    region.parent_region_id = parent_region_id
    db.session.commit()
    db.session.refresh(region)
    return {
        "region_id": region.region_id,
        "region_name": region.region_name,
        "region_description": region.region_description,
        "region_type": region.region_type,
        "distribution_level": region.distribution_level,
        "parent_region_id": region.parent_region_id,
    }, 200


@admin_bp.delete("/regions/<int:region_id>")
@require_permissions("admin.manage")
def delete_region(region_id: int) -> tuple[dict[str, str], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    region = db.session.get(Region, region_id)
    if region is None:
        return {"message": "region not found"}, 404
    has_children = db.session.query(Region.region_id).filter(Region.parent_region_id == region_id).first()
    if has_children is not None:
        return {"message": "cannot delete region with children; reassign or delete children first"}, 400
    db.session.delete(region)
    db.session.commit()
    return {"message": "deleted"}, 200


@admin_bp.put("/regions/<int:region_id>/defaults")
@require_permissions("admin.manage")
def set_region_defaults(region_id: int) -> tuple[dict[str, object], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    region = db.session.get(Region, region_id)
    if region is None:
        return {"message": "region not found"}, 404

    payload = request.get_json(silent=True) or {}
    default_admin_user_id = payload.get("default_admin_user_id")
    default_ambassador_user_id = payload.get("default_ambassador_user_id")

    if region.region_type == "source":
        if default_admin_user_id is None:
            return {"message": "default_admin_user_id is required for source region"}, 400
        if not isinstance(default_admin_user_id, int):
            return {"message": "default_admin_user_id must be integer"}, 400
        user = db.session.get(User, default_admin_user_id)
        if user is None:
            return {"message": "admin user not found"}, 404
        roles = {r.name for r in user.roles}
        if "admin" not in roles and "super_admin" not in roles:
            return {"message": "default_admin_user_id must belong to admin/super_admin"}, 400
        default_ambassador_user_id = None
    elif region.region_type == "distribution":
        if default_ambassador_user_id is None:
            return {"message": "default_ambassador_user_id is required for distribution region"}, 400
        if not isinstance(default_ambassador_user_id, int):
            return {"message": "default_ambassador_user_id must be integer"}, 400
        user = db.session.get(User, default_ambassador_user_id)
        if user is None:
            return {"message": "ambassador user not found"}, 404
        roles = {r.name for r in user.roles}
        if "ambassador" not in roles:
            return {"message": "default_ambassador_user_id must belong to ambassador"}, 400
        default_admin_user_id = None
    else:
        return {"message": "unsupported region type for defaults"}, 400

    region_default = db.session.query(RegionDefault).filter_by(region_id=region_id).one_or_none()
    if region_default is None:
        region_default = RegionDefault(
            region_id=region_id,
            default_admin_user_id=default_admin_user_id,
            default_ambassador_user_id=default_ambassador_user_id,
        )
        db.session.add(region_default)
    else:
        region_default.default_admin_user_id = default_admin_user_id
        region_default.default_ambassador_user_id = default_ambassador_user_id

    db.session.commit()
    db.session.refresh(region_default)

    return {
        "region_id": region_id,
        "default_admin_user_id": region_default.default_admin_user_id,
        "default_ambassador_user_id": region_default.default_ambassador_user_id,
    }, 200


@admin_bp.post("/regions/distribution/regroup-local")
@require_permissions("admin.manage")
def regroup_local_regions_to_minor() -> tuple[dict[str, object], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    payload = request.get_json(silent=True) or {}
    major_region_id = payload.get("major_region_id")
    new_minor_name = str(payload.get("new_minor_name", "")).strip()
    new_minor_description = str(payload.get("new_minor_description", "")).strip() or None
    local_region_ids = payload.get("local_region_ids")

    if not isinstance(major_region_id, int):
        return {"message": "major_region_id must be integer"}, 400
    if not isinstance(local_region_ids, list) or not local_region_ids:
        return {"message": "local_region_ids must be a non-empty list"}, 400
    if any(not isinstance(v, int) for v in local_region_ids):
        return {"message": "local_region_ids must contain integers only"}, 400
    if len(new_minor_name) == 0:
        return {"message": "new_minor_name is required"}, 400
    if len(new_minor_name) > 150:
        return {"message": "new_minor_name exceeds max length 150"}, 400
    if new_minor_description and len(new_minor_description) > 1500:
        return {"message": "new_minor_description exceeds max length 1500"}, 400

    major = db.session.get(Region, major_region_id)
    if major is None:
        return {"message": "major distribution region not found"}, 404
    if major.region_type != "distribution" or major.distribution_level != "major":
        return {"message": "major_region_id must reference a major distribution region"}, 400

    existing_minor = (
        db.session.query(Region)
        .filter(Region.region_name == new_minor_name, Region.region_type == "distribution")
        .one_or_none()
    )
    if existing_minor is not None:
        return {"message": "a distribution region with the same name already exists"}, 409

    locals_rows = (
        db.session.query(Region)
        .filter(Region.region_id.in_(local_region_ids), Region.region_type == "distribution")
        .all()
    )
    if len(locals_rows) != len(set(local_region_ids)):
        return {"message": "one or more local regions not found"}, 404

    for local_region in locals_rows:
        if local_region.distribution_level != "local":
            return {"message": f"region {local_region.region_id} is not a local distribution region"}, 400
        if local_region.parent_region_id is None:
            return {"message": f"region {local_region.region_id} has no parent minor region"}, 400
        parent_minor = db.session.get(Region, local_region.parent_region_id)
        if (
            parent_minor is None
            or parent_minor.region_type != "distribution"
            or parent_minor.distribution_level != "minor"
            or parent_minor.parent_region_id != major_region_id
        ):
            return {
                "message": (
                    f"region {local_region.region_id} does not belong to a minor region under major {major_region_id}"
                )
            }, 400

    new_minor = Region(
        region_name=new_minor_name,
        region_description=new_minor_description,
        region_type="distribution",
        distribution_level="minor",
        parent_region_id=major_region_id,
    )
    db.session.add(new_minor)
    db.session.flush()

    for local_region in locals_rows:
        local_region.parent_region_id = new_minor.region_id

    db.session.commit()
    db.session.refresh(new_minor)
    return {
        "message": "local regions regrouped under new minor distribution region",
        "new_minor_region": {
            "region_id": new_minor.region_id,
            "region_name": new_minor.region_name,
            "region_description": new_minor.region_description,
            "region_type": new_minor.region_type,
            "distribution_level": new_minor.distribution_level,
            "parent_region_id": new_minor.parent_region_id,
        },
        "moved_local_region_ids": sorted(set(local_region_ids)),
    }, 201


@admin_bp.get("/products")
@require_permissions("product.read")
def list_products() -> tuple[dict[str, list[dict[str, object]]], int]:
    products = db.session.query(Product).order_by(Product.product_name.asc()).all()
    return {
        "items": [
            {
                "id": product.id,
                "product_name": product.product_name,
                "product_type": product.product_type,
                "product_unit": product.product_unit,
                "validity_days": product.validity_days,
            }
            for product in products
        ]
    }, 200


@admin_bp.get("/product-types")
@require_permissions("product.read")
def list_product_types() -> tuple[dict[str, list[dict[str, object]]], int]:
    rows = (
        db.session.query(
            ProductType,
            db.func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, Product.product_type == ProductType.product_type)
        .group_by(ProductType.id)
        .order_by(ProductType.product_type.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": product_type.id,
                "product_type": product_type.product_type,
                "product_count": int(product_count),
            }
            for product_type, product_count in rows
        ]
    }, 200


@admin_bp.post("/product-types")
@require_permissions("product.manage")
def create_product_type() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    product_type = str(payload.get("product_type", "")).strip()
    if not product_type:
        return {"message": "product_type is required"}, 400
    if len(product_type) > 50:
        return {"message": "product_type exceeds max length 50"}, 400

    existing = (
        db.session.query(ProductType)
        .filter(db.func.lower(ProductType.product_type) == product_type.lower())
        .first()
    )
    if existing is not None:
        return {"message": "product_type already exists"}, 409

    row = ProductType(product_type=product_type)
    db.session.add(row)
    db.session.commit()
    db.session.refresh(row)
    return {
        "id": row.id,
        "product_type": row.product_type,
    }, 201


@admin_bp.delete("/product-types/<int:product_type_id>")
@require_permissions("product.manage")
def delete_product_type(product_type_id: int) -> tuple[dict[str, object], int]:
    row = db.session.get(ProductType, product_type_id)
    if row is None:
        return {"message": "product_type not found"}, 404

    linked_products = (
        db.session.query(Product.id)
        .filter(Product.product_type == row.product_type)
        .limit(1)
        .first()
    )
    if linked_products is not None:
        return {"message": "cannot delete product_type with associated products"}, 409

    db.session.delete(row)
    db.session.commit()
    return {"message": "deleted"}, 200


@admin_bp.post("/products")
@require_permissions("product.manage")
def create_product() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    product_name = str(payload.get("product_name", "")).strip()
    product_type = str(payload.get("product_type", "")).strip()
    product_unit = str(payload.get("product_unit", "")).strip()
    validity_days = payload.get("validity_days")

    validation_error = _validate_product_fields(product_name, product_type, product_unit, validity_days)
    if validation_error:
        return {"message": validation_error}, 400
    canonical_type = _canonical_product_type(product_type)
    if canonical_type is None:
        return {"message": "invalid product_type; choose one from product_types"}, 400

    product = Product(
        product_name=product_name,
        product_type=canonical_type,
        product_unit=product_unit,
        validity_days=validity_days,
    )
    db.session.add(product)
    db.session.commit()
    db.session.refresh(product)
    return {
        "id": product.id,
        "product_name": product.product_name,
        "product_type": product.product_type,
        "product_unit": product.product_unit,
        "validity_days": product.validity_days,
    }, 201


@admin_bp.put("/products/<int:product_id>")
@require_permissions("product.manage")
def update_product(product_id: int) -> tuple[dict[str, object], int]:
    product = db.session.get(Product, product_id)
    if product is None:
        return {"message": "product not found"}, 404

    payload = request.get_json(silent=True) or {}
    product_name = str(payload.get("product_name", "")).strip()
    product_type = str(payload.get("product_type", "")).strip()
    product_unit = str(payload.get("product_unit", "")).strip()
    validity_days = payload.get("validity_days")

    validation_error = _validate_product_fields(product_name, product_type, product_unit, validity_days)
    if validation_error:
        return {"message": validation_error}, 400
    canonical_type = _canonical_product_type(product_type)
    if canonical_type is None:
        return {"message": "invalid product_type; choose one from product_types"}, 400

    product.product_name = product_name
    product.product_type = canonical_type
    product.product_unit = product_unit
    product.validity_days = validity_days
    db.session.commit()
    db.session.refresh(product)
    return {
        "id": product.id,
        "product_name": product.product_name,
        "product_type": product.product_type,
        "product_unit": product.product_unit,
        "validity_days": product.validity_days,
    }, 200


@admin_bp.delete("/products/<int:product_id>")
@require_permissions("product.manage")
def delete_product(product_id: int) -> tuple[dict[str, str], int]:
    product = db.session.get(Product, product_id)
    if product is None:
        return {"message": "product not found"}, 404

    db.session.delete(product)
    db.session.commit()
    return {"message": "deleted"}, 200


@admin_bp.get("/suppliers")
@require_permissions("supplier.read")
def list_suppliers() -> tuple[dict[str, list[dict[str, object]]], int]:
    suppliers = db.session.query(Supplier).order_by(Supplier.supplier_name.asc()).all()
    supplier_links = db.session.query(SupplierProduct).order_by(SupplierProduct.id.asc()).all()
    links_by_supplier: dict[int, list[SupplierProduct]] = {}
    for link in supplier_links:
        links_by_supplier.setdefault(link.supplier_id, []).append(link)

    avg_rating_rows = (
        db.session.query(
            ProcurementOrderReview.supplier_id,
            db.func.avg(ProcurementOrderReview.rating),
            db.func.count(ProcurementOrderReview.review_id),
        )
        .group_by(ProcurementOrderReview.supplier_id)
        .all()
    )
    avg_rating_by_supplier = {
        row[0]: {"overall_rating": round(float(row[1]), 2), "rating_count": int(row[2])}
        for row in avg_rating_rows
    }

    return {
        "items": [
            {
                "supplier_id": s.supplier_id,
                "supplier_name": s.supplier_name,
                "email": s.email,
                "address_line1": s.address_line1,
                "address_line2": s.address_line2,
                "address_line3": s.address_line3,
                "phone_number": s.phone_number,
                "is_active": s.is_active,
                "product_links": [
                    {
                        "product_id": link.product_id,
                        "supplier_type": link.supplier_type,
                    }
                    for link in links_by_supplier.get(s.supplier_id, [])
                ],
                "overall_rating": avg_rating_by_supplier.get(s.supplier_id, {}).get("overall_rating"),
                "rating_count": avg_rating_by_supplier.get(s.supplier_id, {}).get("rating_count", 0),
            }
            for s in suppliers
        ]
    }, 200


@admin_bp.get("/suppliers/<int:supplier_id>")
@require_permissions("supplier.read")
def get_supplier_detail(supplier_id: int) -> tuple[dict[str, object], int]:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return {"message": "supplier not found"}, 404

    links = (
        db.session.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == supplier_id)
        .order_by(SupplierProduct.id.asc())
        .all()
    )
    rating_breakdown_rows = (
        db.session.query(ProcurementOrderReview.rating, db.func.count(ProcurementOrderReview.review_id))
        .filter(ProcurementOrderReview.supplier_id == supplier_id)
        .group_by(ProcurementOrderReview.rating)
        .order_by(ProcurementOrderReview.rating.desc())
        .all()
    )
    rating_breakdown = [{"rating": int(row[0]), "orders": int(row[1])} for row in rating_breakdown_rows]
    review_rows = (
        db.session.query(ProcurementOrderReview)
        .filter(ProcurementOrderReview.supplier_id == supplier_id)
        .order_by(ProcurementOrderReview.rating.desc(), ProcurementOrderReview.created_at.desc())
        .all()
    )
    procurement_ids = {row.procurement_id for row in review_rows}
    if procurement_ids:
        orders = (
            db.session.query(ProcurementOrder)
            .filter(ProcurementOrder.procurement_id.in_(procurement_ids))
            .all()
        )
    else:
        orders = []
    orders_by_id = {order.procurement_id: order for order in orders}
    average = (
        db.session.query(db.func.avg(ProcurementOrderReview.rating))
        .filter(ProcurementOrderReview.supplier_id == supplier_id)
        .scalar()
    )
    overall_rating = round(float(average), 2) if average is not None else None

    return {
        "supplier_id": supplier.supplier_id,
        "supplier_name": supplier.supplier_name,
        "email": supplier.email,
        "address_line1": supplier.address_line1,
        "address_line2": supplier.address_line2,
        "address_line3": supplier.address_line3,
        "phone_number": supplier.phone_number,
        "is_active": supplier.is_active,
        "product_links": [{"product_id": link.product_id, "supplier_type": link.supplier_type} for link in links],
        "overall_rating": overall_rating,
        "rating_count": sum(item["orders"] for item in rating_breakdown),
        "rating_breakdown": rating_breakdown,
        "reviews": [
            {
                "review_id": row.review_id,
                "procurement_id": row.procurement_id,
                "procurement_status": orders_by_id[row.procurement_id].status if row.procurement_id in orders_by_id else None,
                "rating": row.rating,
                "review_text": row.review_text,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in review_rows
        ],
    }, 200


@admin_bp.get("/suppliers/options")
@require_permissions("supplier.read")
def supplier_options() -> tuple[dict[str, list[dict[str, object]]], int]:
    suppliers = (
        db.session.query(Supplier)
        .filter(Supplier.is_active.is_(True))
        .order_by(Supplier.supplier_name.asc())
        .all()
    )
    return {
        "items": [
            {
                "supplier_id": s.supplier_id,
                "supplier_name": s.supplier_name,
                "email": s.email,
            }
            for s in suppliers
        ]
    }, 200


@admin_bp.post("/suppliers")
@require_permissions("supplier.manage")
def create_supplier() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    supplier_name = str(payload.get("supplier_name", "")).strip()
    email = _optional_trimmed_str(payload.get("email"))
    address_line1 = _optional_trimmed_str(payload.get("address_line1"))
    address_line2 = _optional_trimmed_str(payload.get("address_line2"))
    address_line3 = _optional_trimmed_str(payload.get("address_line3"))
    phone_number = _optional_trimmed_str(payload.get("phone_number"))
    product_links = payload.get("product_links", [])
    is_active = payload.get("is_active", True)

    validation_error = _validate_supplier_fields(
        supplier_name=supplier_name,
        email=email,
        product_links=product_links,
        is_active=is_active,
        address_line1=address_line1,
        address_line2=address_line2,
        address_line3=address_line3,
        phone_number=phone_number,
    )
    if validation_error:
        return {"message": validation_error}, 400

    existing = db.session.query(Supplier).filter(Supplier.supplier_name == supplier_name).one_or_none()
    if existing is not None:
        return {"message": "supplier_name already exists"}, 409

    supplier = Supplier(
        supplier_name=supplier_name,
        email=email,
        address_line1=address_line1,
        address_line2=address_line2,
        address_line3=address_line3,
        phone_number=phone_number,
        is_active=is_active,
    )
    db.session.add(supplier)
    db.session.flush()

    normalized_links = _normalize_supplier_product_links(product_links)
    for link in normalized_links:
        product = db.session.get(Product, link["product_id"])
        if product is None:
            db.session.rollback()
            return {"message": f"product not found: {link['product_id']}"}, 404
        db.session.add(
            SupplierProduct(
                supplier_id=supplier.supplier_id,
                product_id=link["product_id"],
                supplier_type=link["supplier_type"],
            )
        )

    db.session.commit()
    db.session.refresh(supplier)
    return {
        "supplier_id": supplier.supplier_id,
        "supplier_name": supplier.supplier_name,
        "email": supplier.email,
        "address_line1": supplier.address_line1,
        "address_line2": supplier.address_line2,
        "address_line3": supplier.address_line3,
        "phone_number": supplier.phone_number,
        "is_active": supplier.is_active,
        "product_links": normalized_links,
    }, 201


@admin_bp.put("/suppliers/<int:supplier_id>")
@require_permissions("supplier.manage")
def update_supplier(supplier_id: int) -> tuple[dict[str, object], int]:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return {"message": "supplier not found"}, 404

    payload = request.get_json(silent=True) or {}
    supplier_name = str(payload.get("supplier_name", "")).strip()
    email = _optional_trimmed_str(payload.get("email"))
    address_line1 = _optional_trimmed_str(payload.get("address_line1"))
    address_line2 = _optional_trimmed_str(payload.get("address_line2"))
    address_line3 = _optional_trimmed_str(payload.get("address_line3"))
    phone_number = _optional_trimmed_str(payload.get("phone_number"))
    product_links = payload.get("product_links", [])
    is_active = payload.get("is_active", True)

    validation_error = _validate_supplier_fields(
        supplier_name=supplier_name,
        email=email,
        product_links=product_links,
        is_active=is_active,
        address_line1=address_line1,
        address_line2=address_line2,
        address_line3=address_line3,
        phone_number=phone_number,
    )
    if validation_error:
        return {"message": validation_error}, 400

    existing = (
        db.session.query(Supplier)
        .filter(Supplier.supplier_name == supplier_name, Supplier.supplier_id != supplier_id)
        .one_or_none()
    )
    if existing is not None:
        return {"message": "supplier_name already exists"}, 409

    normalized_links = _normalize_supplier_product_links(product_links)
    for link in normalized_links:
        product = db.session.get(Product, link["product_id"])
        if product is None:
            return {"message": f"product not found: {link['product_id']}"}, 404

    supplier.supplier_name = supplier_name
    supplier.email = email
    supplier.address_line1 = address_line1
    supplier.address_line2 = address_line2
    supplier.address_line3 = address_line3
    supplier.phone_number = phone_number
    supplier.is_active = is_active

    db.session.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).delete()
    for link in normalized_links:
        db.session.add(
            SupplierProduct(
                supplier_id=supplier_id,
                product_id=link["product_id"],
                supplier_type=link["supplier_type"],
            )
        )

    db.session.commit()
    db.session.refresh(supplier)
    return {
        "supplier_id": supplier.supplier_id,
        "supplier_name": supplier.supplier_name,
        "email": supplier.email,
        "address_line1": supplier.address_line1,
        "address_line2": supplier.address_line2,
        "address_line3": supplier.address_line3,
        "phone_number": supplier.phone_number,
        "is_active": supplier.is_active,
        "product_links": normalized_links,
    }, 200


@admin_bp.delete("/suppliers/<int:supplier_id>")
@require_permissions("supplier.manage")
def delete_supplier(supplier_id: int) -> tuple[dict[str, str], int]:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return {"message": "supplier not found"}, 404

    has_procurement = (
        db.session.query(ProcurementOrder.procurement_id)
        .filter(ProcurementOrder.supplier_id == supplier_id)
        .first()
    )
    if has_procurement:
        return {"message": "cannot delete supplier with procurement orders"}, 400

    db.session.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).delete()
    db.session.delete(supplier)
    db.session.commit()
    return {"message": "deleted"}, 200


@admin_bp.get("/procurement-orders")
@require_permissions("procurement.read")
def list_procurement_orders() -> tuple[dict[str, object], int]:
    page = _int_query_arg("page", 1, minimum=1)
    page_size = _int_query_arg("page_size", 20, minimum=1, maximum=100)
    supplier_id = _optional_int_query_arg("supplier_id")
    product_id = _optional_int_query_arg("product_id")
    status = request.args.get("status")

    query = db.session.query(ProcurementOrder)
    if supplier_id is not None:
        query = query.filter(ProcurementOrder.supplier_id == supplier_id)
    if product_id is not None:
        query = query.filter(ProcurementOrder.product_id == product_id)
    if status:
        query = query.filter(ProcurementOrder.status == status)

    total = query.count()
    rows = (
        query.order_by(ProcurementOrder.procurement_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_build_procurement_order_response(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }, 200


@admin_bp.get("/procurement-orders/options")
@require_permissions("procurement.read")
def procurement_order_options() -> tuple[dict[str, object], int]:
    include_draft = request.args.get("include_draft", "false").strip().lower() == "true"
    query = db.session.query(ProcurementOrder)
    if not include_draft:
        query = query.filter(ProcurementOrder.status != "draft")
    rows = query.order_by(ProcurementOrder.procurement_id.desc()).limit(500).all()
    return {"items": [_build_procurement_order_response(row) for row in rows]}, 200


@admin_bp.post("/procurement-orders")
@require_permissions("procurement.manage")
def create_procurement_order() -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    payload = request.get_json(silent=True) or {}
    supplier_id = payload.get("supplier_id")
    product_id = payload.get("product_id")
    quantity = payload.get("quantity")
    price_per_unit_raw = payload.get("price_per_unit")
    procurement_date_raw = payload.get("procurement_date")
    status = str(payload.get("status", "draft")).strip().lower()

    if not isinstance(supplier_id, int):
        return {"message": "supplier_id must be integer"}, 400
    if not isinstance(product_id, int):
        return {"message": "product_id must be integer"}, 400
    if not isinstance(quantity, int) or quantity < 0:
        return {"message": "quantity must be non-negative integer"}, 400
    if status not in {"draft", "placed", "received", "cancelled"}:
        return {"message": "status must be one of draft, placed, received, cancelled"}, 400

    try:
        price_per_unit = Decimal(str(price_per_unit_raw))
    except (InvalidOperation, TypeError, ValueError):
        return {"message": "price_per_unit must be a valid decimal number"}, 400
    if price_per_unit < 0:
        return {"message": "price_per_unit must be non-negative"}, 400

    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return {"message": "supplier not found"}, 404
    product = db.session.get(Product, product_id)
    if product is None:
        return {"message": "product not found"}, 404

    supplier_product_link = (
        db.session.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == supplier_id, SupplierProduct.product_id == product_id)
        .one_or_none()
    )
    if supplier_product_link is None:
        return {"message": "supplier is not linked to selected product"}, 400

    if procurement_date_raw:
        try:
            procurement_date = datetime.fromisoformat(str(procurement_date_raw))
            if procurement_date.tzinfo is None:
                procurement_date = procurement_date.replace(tzinfo=timezone.utc)
        except ValueError:
            return {"message": "procurement_date must be ISO date/time format"}, 400
    else:
        procurement_date = datetime.now(timezone.utc)

    order = ProcurementOrder(
        supplier_id=supplier_id,
        product_id=product_id,
        quantity=quantity,
        price_per_unit=price_per_unit,
        procurement_date=procurement_date,
        status=status,
        created_by_admin_user_id=current_user_id,
    )
    db.session.add(order)
    db.session.commit()
    db.session.refresh(order)
    return _build_procurement_order_response(order), 201


@admin_bp.patch("/procurement-orders/<int:procurement_id>/status")
@require_permissions("procurement.manage")
def update_procurement_order_status(procurement_id: int) -> tuple[dict[str, object], int]:
    order = db.session.get(ProcurementOrder, procurement_id)
    if order is None:
        return {"message": "procurement order not found"}, 404
    if order.pushed_to_inventory:
        return {"message": "cannot change status after order is pushed to inventory"}, 409

    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"draft", "placed", "received", "cancelled"}:
        return {"message": "status must be one of draft, placed, received, cancelled"}, 400

    order.status = status
    db.session.commit()
    db.session.refresh(order)
    return _build_procurement_order_response(order), 200


@admin_bp.post("/procurement-orders/<int:procurement_id>/push-to-inventory")
@require_permissions("inventory.update")
def push_procurement_order_to_inventory(procurement_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    roles = _roles_set()
    if "admin" not in roles and "super_admin" not in roles:
        return {"message": "Forbidden"}, 403

    order = db.session.get(ProcurementOrder, procurement_id)
    if order is None:
        return {"message": "procurement order not found"}, 404
    if order.status != "received":
        return {"message": "only received procurement orders can be pushed to inventory"}, 400
    if order.pushed_to_inventory:
        return {"message": "procurement order already pushed to inventory"}, 409

    supplier = db.session.get(Supplier, order.supplier_id)
    if supplier is None:
        return {"message": "supplier not found"}, 404
    link = (
        db.session.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == order.supplier_id, SupplierProduct.product_id == order.product_id)
        .one_or_none()
    )
    if link is None:
        return {"message": "supplier-product link not found"}, 400

    existing_item = (
        db.session.query(InventoryItem)
        .filter(
            InventoryItem.origin_type == "procurement",
            InventoryItem.product_id == order.product_id,
            InventoryItem.supplier_id == order.supplier_id,
        )
        .one_or_none()
    )

    if existing_item is not None:
        existing_item.quantity += order.quantity
        existing_item.origin = link.supplier_type
        existing_item.created_by_admin_user_id = current_user_id
        order.pushed_to_inventory = True
        db.session.commit()
        db.session.refresh(existing_item)
        return {
            "message": "inventory updated from procurement order",
            "inventory_item": _build_inventory_item_response(existing_item),
        }, 200

    item = InventoryItem(
        product_id=order.product_id,
        seller_id=None,
        supplier_id=order.supplier_id,
        origin_type="procurement",
        origin=link.supplier_type,
        entry_date=datetime.now(timezone.utc),
        quantity=order.quantity,
        created_by_admin_user_id=current_user_id,
    )
    db.session.add(item)
    order.pushed_to_inventory = True
    db.session.commit()
    db.session.refresh(item)
    return {
        "message": "inventory created from procurement order",
        "inventory_item": _build_inventory_item_response(item),
    }, 201


@admin_bp.get("/procurement-orders/<int:procurement_id>/reviews")
@require_permissions("supplier.rating.read")
def list_procurement_reviews(procurement_id: int) -> tuple[dict[str, object], int]:
    order = db.session.get(ProcurementOrder, procurement_id)
    if order is None:
        return {"message": "procurement order not found"}, 404
    rows = (
        db.session.query(ProcurementOrderReview)
        .filter(ProcurementOrderReview.procurement_id == procurement_id)
        .order_by(ProcurementOrderReview.review_id.desc())
        .all()
    )
    return {"items": [_build_procurement_review_response(row, order_status=order.status) for row in rows]}, 200


@admin_bp.post("/procurement-orders/<int:procurement_id>/reviews")
@require_permissions("supplier.rating.manage")
def create_procurement_review(procurement_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    order = db.session.get(ProcurementOrder, procurement_id)
    if order is None:
        return {"message": "procurement order not found"}, 404
    if order.status == "draft":
        return {"message": "cannot review a draft procurement order"}, 400

    if request.content_type and "multipart/form-data" in request.content_type:
        rating_raw = request.form.get("rating")
        review_text = _optional_trimmed_str(request.form.get("review_text"))
        files = request.files.getlist("images")
    else:
        payload = request.get_json(silent=True) or {}
        rating_raw = payload.get("rating")
        review_text = _optional_trimmed_str(payload.get("review_text"))
        files = []

    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        return {"message": "rating must be integer"}, 400
    if not isinstance(rating, int):
        return {"message": "rating must be integer"}, 400
    if rating < 1 or rating > 10:
        return {"message": "rating must be between 1 and 10"}, 400

    existing = (
        db.session.query(ProcurementOrderReview)
        .filter(ProcurementOrderReview.procurement_id == procurement_id)
        .one_or_none()
    )
    is_update = existing is not None
    if existing is None:
        row = ProcurementOrderReview(
            procurement_id=procurement_id,
            supplier_id=order.supplier_id,
            product_id=order.product_id,
            rating=rating,
            review_text=review_text,
            reviewed_by_user_id=current_user_id,
        )
        db.session.add(row)
        db.session.flush()
    else:
        row = existing
        row.rating = rating
        row.reviewed_by_user_id = current_user_id
        if review_text:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if row.review_text:
                row.review_text = f"{row.review_text}\n\n[{timestamp}] {review_text}"
            else:
                row.review_text = f"[{timestamp}] {review_text}"

    image_rows: list[ProcurementOrderReviewImage] = []
    for file in files:
        if not file or not file.filename:
            continue
        stored_relative_path, error = _save_procurement_review_image(file, row.review_id)
        if error:
            db.session.rollback()
            return {"message": error}, 400
        image_row = ProcurementOrderReviewImage(review_id=row.review_id, file_path=stored_relative_path)
        db.session.add(image_row)
        image_rows.append(image_row)

    db.session.commit()
    db.session.refresh(row)
    status_code = 200 if is_update else 201
    response = _build_procurement_review_response(row, order_status=order.status)
    response["message"] = "review updated" if is_update else "review created"
    return response, status_code


@admin_bp.get("/procurement-review-images/<path:filename>")
@require_permissions("supplier.rating.read")
def get_procurement_review_image(filename: str):
    images_root = os.path.join(current_app.instance_path, "uploads", "procurement_reviews")
    return send_from_directory(images_root, filename)


@admin_bp.post("/super-admin/users/<int:user_id>/admin")
@require_permissions("admin.manage")
def grant_admin_role(user_id: int) -> tuple[dict[str, object], int]:
    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    admin_role = find_role_by_name("admin")
    if admin_role is None:
        return {"message": "admin role not found"}, 500

    roles_by_name = {role.name: role for role in user.roles}
    roles_by_name[admin_role.name] = admin_role
    updated_user = assign_roles_to_user(user, sorted(roles_by_name.values(), key=lambda r: r.name))

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "roles": sorted(role.name for role in updated_user.roles),
    }, 200


@admin_bp.delete("/super-admin/users/<int:user_id>/admin")
@require_permissions("admin.manage")
def revoke_admin_role(user_id: int) -> tuple[dict[str, object], int]:
    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    updated_roles = [role for role in user.roles if role.name != "admin"]
    updated_user = assign_roles_to_user(user, updated_roles)

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "roles": sorted(role.name for role in updated_user.roles),
    }, 200


@admin_bp.post("/super-admin/users/<int:user_id>/ambassador")
@require_permissions("admin.manage")
def grant_ambassador_role(user_id: int) -> tuple[dict[str, object], int]:
    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    ambassador_role = find_role_by_name("ambassador")
    if ambassador_role is None:
        return {"message": "ambassador role not found"}, 500

    roles_by_name = {role.name: role for role in user.roles}
    roles_by_name[ambassador_role.name] = ambassador_role
    updated_user = assign_roles_to_user(user, sorted(roles_by_name.values(), key=lambda r: r.name))

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "roles": sorted(role.name for role in updated_user.roles),
    }, 200


@admin_bp.delete("/super-admin/users/<int:user_id>/ambassador")
@require_permissions("admin.manage")
def revoke_ambassador_role(user_id: int) -> tuple[dict[str, object], int]:
    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    updated_roles = [role for role in user.roles if role.name != "ambassador"]
    updated_user = assign_roles_to_user(user, updated_roles)

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "roles": sorted(role.name for role in updated_user.roles),
    }, 200


@admin_bp.patch("/sellers/<int:user_id>/status")
@require_permissions("seller.validate")
def set_seller_status(user_id: int) -> tuple[dict[str, object], int]:
    if not _is_admin_like():
        return {"message": "Forbidden"}, 403

    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "")).strip().lower()
    allowed = {"pending_validation", "valid", "rejected"}
    if status not in allowed:
        return {"message": "status must be one of pending_validation, valid, rejected"}, 400

    user = find_user_by_id(user_id)
    if user is None:
        return {"message": "user not found"}, 404

    roles = {role.name for role in user.roles}
    if "seller" not in roles:
        return {"message": "target user is not a seller"}, 400
    if not _is_super_admin():
        current_user_id = _current_user_id_from_token()
        if current_user_id is None:
            return {"message": "invalid token identity"}, 401
        if user.assigned_admin_user_id != current_user_id:
            return {"message": "seller is not assigned to current admin"}, 403

    updated = update_seller_status(user, status)
    return {
        "id": updated.id,
        "email": updated.email,
        "roles": sorted(role.name for role in updated.roles),
        "seller_status": updated.seller_status,
        "assigned_admin_user_id": updated.assigned_admin_user_id,
    }, 200


@admin_bp.get("/sellers/validation-queue")
@require_permissions("seller.validate")
def seller_validation_queue() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    query = db.session.query(User).filter(User.roles.any(name="seller"))
    if not _is_super_admin():
        query = query.filter(User.assigned_admin_user_id == current_user_id)

    sellers = query.order_by(User.id.asc()).all()
    return {
        "items": [
            {
                "id": s.id,
                "email": s.email,
                "roles": sorted(role.name for role in s.roles),
                "first_name": s.first_name,
                "last_name": s.last_name,
                "seller_status": s.seller_status,
                "assigned_admin_user_id": s.assigned_admin_user_id,
            }
            for s in sellers
        ]
    }, 200


@admin_bp.patch("/sellers/<int:user_id>/assigned-admin")
@require_permissions("admin.manage")
def reassign_seller_admin(user_id: int) -> tuple[dict[str, object], int]:
    if not _is_super_admin():
        return {"message": "Forbidden"}, 403

    seller = find_user_by_id(user_id)
    if seller is None:
        return {"message": "seller not found"}, 404
    seller_roles = {r.name for r in seller.roles}
    if "seller" not in seller_roles:
        return {"message": "target user is not seller"}, 400

    payload = request.get_json(silent=True) or {}
    assigned_admin_user_id = payload.get("assigned_admin_user_id")
    if not isinstance(assigned_admin_user_id, int):
        return {"message": "assigned_admin_user_id must be integer"}, 400

    admin_user = find_user_by_id(assigned_admin_user_id)
    if admin_user is None:
        return {"message": "admin user not found"}, 404
    admin_roles = {r.name for r in admin_user.roles}
    if not ({"admin", "super_admin"} & admin_roles):
        return {"message": "assigned admin user must have admin/super_admin role"}, 400

    updated = update_seller_assigned_admin(seller, assigned_admin_user_id)
    return {
        "id": updated.id,
        "email": updated.email,
        "seller_status": updated.seller_status,
        "assigned_admin_user_id": updated.assigned_admin_user_id,
    }, 200


@admin_bp.post("/ambassadors/<int:ambassador_user_id>/buyers/<int:buyer_user_id>")
@require_permissions("buyer.group.manage")
def assign_buyer_group(ambassador_user_id: int, buyer_user_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    ambassador = find_user_by_id(ambassador_user_id)
    buyer = find_user_by_id(buyer_user_id)
    if ambassador is None or buyer is None:
        return {"message": "user not found"}, 404

    ambassador_roles = {role.name for role in ambassador.roles}
    buyer_roles = {role.name for role in buyer.roles}
    if "ambassador" not in ambassador_roles:
        return {"message": "target ambassador user must have ambassador role"}, 400
    if "buyer" not in buyer_roles:
        return {"message": "target buyer user must have buyer role"}, 400

    if not _is_admin_like():
        if "ambassador" not in _roles_set():
            return {"message": "Forbidden"}, 403
        allowed_ambassador_ids, allowed_buyer_ids = _allowed_group_scope_for_ambassador(current_user_id)
        if ambassador_user_id not in allowed_ambassador_ids:
            return {"message": "target ambassador is outside your managed region scope"}, 403
        if buyer_user_id not in allowed_buyer_ids:
            return {"message": "buyer is outside your managed region scope"}, 403

    assign_buyer_to_ambassador(ambassador_user_id, buyer_user_id)
    return {"message": "assigned"}, 200


@admin_bp.delete("/ambassadors/<int:ambassador_user_id>/buyers/<int:buyer_user_id>")
@require_permissions("buyer.group.manage")
def remove_buyer_group(ambassador_user_id: int, buyer_user_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    if not _is_admin_like():
        if "ambassador" not in _roles_set():
            return {"message": "Forbidden"}, 403
        allowed_ambassador_ids, allowed_buyer_ids = _allowed_group_scope_for_ambassador(current_user_id)
        if ambassador_user_id not in allowed_ambassador_ids:
            return {"message": "target ambassador is outside your managed region scope"}, 403
        if buyer_user_id not in allowed_buyer_ids:
            return {"message": "buyer is outside your managed region scope"}, 403

    removed = remove_buyer_from_ambassador(ambassador_user_id, buyer_user_id)
    if not removed:
        return {"message": "assignment not found"}, 404
    return {"message": "removed"}, 200


@admin_bp.get("/buyer-groups/options")
@require_permissions("buyer.group.read")
def buyer_group_options() -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    if _is_admin_like():
        users = list_users()
        return {
            "owned_regions": [],
            "selected_region_id": None,
            "ambassadors": [_build_user_row(u) for u in users if any(r.name == "ambassador" for r in u.roles)],
            "buyers": [_build_user_row(u) for u in users if any(r.name == "buyer" for r in u.roles)],
        }, 200

    if "ambassador" not in _roles_set():
        return {"message": "Forbidden"}, 403

    owned_regions = _owned_distribution_regions_for_ambassador(current_user_id)
    if not owned_regions:
        return {"owned_regions": [], "selected_region_id": None, "ambassadors": [], "buyers": []}, 200

    owned_region_ids = {region.region_id for region in owned_regions}
    requested_region_id = _optional_int_query_arg("region_id")
    selected_region_id = requested_region_id or owned_regions[0].region_id
    if selected_region_id not in owned_region_ids:
        return {"message": "region_id is outside ambassador managed regions"}, 403

    selected_region = next(region for region in owned_regions if region.region_id == selected_region_id)
    ambassador_ids, buyer_ids = _scope_user_ids_for_region(selected_region, current_user_id)

    ambassadors = (
        db.session.query(User)
        .filter(User.id.in_(ambassador_ids), User.roles.any(name="ambassador"))
        .order_by(User.id.asc())
        .all()
        if ambassador_ids
        else []
    )
    buyers = (
        db.session.query(User)
        .filter(User.id.in_(buyer_ids), User.roles.any(name="buyer"))
        .order_by(User.id.asc())
        .all()
        if buyer_ids
        else []
    )

    return {
        "owned_regions": [
            {
                "region_id": region.region_id,
                "region_name": region.region_name,
                "distribution_level": region.distribution_level,
                "parent_region_id": region.parent_region_id,
            }
            for region in owned_regions
        ],
        "selected_region_id": selected_region_id,
        "ambassadors": [_build_user_row(u) for u in ambassadors],
        "buyers": [_build_user_row(u) for u in buyers],
    }, 200


@admin_bp.get("/ambassadors/<int:ambassador_user_id>/buyers")
@require_permissions("buyer.group.read")
def list_buyer_group(ambassador_user_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    if not _is_admin_like():
        if "ambassador" not in _roles_set():
            return {"message": "Forbidden"}, 403
        allowed_ambassador_ids, _ = _allowed_group_scope_for_ambassador(current_user_id)
        if ambassador_user_id not in allowed_ambassador_ids:
            return {"message": "target ambassador is outside your managed region scope"}, 403

    buyers = list_buyers_for_ambassador(ambassador_user_id)
    return {
        "items": [
            {
                "id": buyer.id,
                "email": buyer.email,
                "first_name": buyer.first_name,
                "last_name": buyer.last_name,
                "phone_number": buyer.phone_number,
                "region": buyer.region,
            }
            for buyer in buyers
        ]
    }, 200


def _current_user_id_from_token() -> int | None:
    raw_identity = get_jwt_identity()
    try:
        return int(raw_identity)
    except (TypeError, ValueError):
        return None


def _roles_set() -> set[str]:
    claims = get_jwt()
    return set(claims.get("roles", []))


def _is_admin_like() -> bool:
    roles = _roles_set()
    return bool({"admin", "super_admin"} & roles)


def _is_super_admin() -> bool:
    roles = _roles_set()
    return "super_admin" in roles


def _source_region_ids_for_admin(admin_user_id: int) -> list[int]:
    rows = db.session.query(RegionDefault.region_id).filter(
        RegionDefault.default_admin_user_id == admin_user_id
    )
    return [row[0] for row in rows.all()]


def _seller_is_in_admin_source_regions(admin_user_id: int, seller: User) -> bool:
    region_ids = _source_region_ids_for_admin(admin_user_id)
    if not region_ids:
        return False
    return seller.source_region_id in set(region_ids)


def _can_ambassador_manage_buyer(ambassador_user_id: int, buyer: User) -> bool:
    if buyer.major_distribution_region_id is None:
        return False

    region_default = (
        db.session.query(RegionDefault)
        .filter(RegionDefault.region_id == buyer.major_distribution_region_id)
        .one_or_none()
    )
    if (
        region_default is not None
        and region_default.default_ambassador_user_id == ambassador_user_id
    ):
        return True

    assignment = (
        db.session.query(AmbassadorBuyerAssignment)
        .filter(
            AmbassadorBuyerAssignment.ambassador_user_id == ambassador_user_id,
            AmbassadorBuyerAssignment.buyer_user_id == buyer.id,
        )
        .one_or_none()
    )
    return assignment is not None


def _build_procurement_order_response(order: ProcurementOrder) -> dict[str, object]:
    supplier = db.session.get(Supplier, order.supplier_id)
    product = db.session.get(Product, order.product_id)
    return {
        "procurement_id": order.procurement_id,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.supplier_name if supplier else None,
        "product_id": order.product_id,
        "product_name": product.product_name if product else None,
        "quantity": order.quantity,
        "price_per_unit": str(order.price_per_unit),
        "total_value": str(order.price_per_unit * order.quantity),
        "procurement_date": order.procurement_date.isoformat() if order.procurement_date else None,
        "status": order.status,
        "pushed_to_inventory": order.pushed_to_inventory,
        "created_by_admin_user_id": order.created_by_admin_user_id,
    }


def _build_procurement_review_response(
    row: ProcurementOrderReview, *, order_status: str | None = None
) -> dict[str, object]:
    supplier = db.session.get(Supplier, row.supplier_id)
    product = db.session.get(Product, row.product_id)
    rated_by = db.session.get(User, row.reviewed_by_user_id)
    if order_status is None:
        order = db.session.get(ProcurementOrder, row.procurement_id)
        order_status = order.status if order else None
    image_rows = (
        db.session.query(ProcurementOrderReviewImage)
        .filter(ProcurementOrderReviewImage.review_id == row.review_id)
        .order_by(ProcurementOrderReviewImage.image_id.asc())
        .all()
    )
    return {
        "review_id": row.review_id,
        "procurement_id": row.procurement_id,
        "procurement_status": order_status,
        "supplier_id": row.supplier_id,
        "supplier_name": supplier.supplier_name if supplier else None,
        "product_id": row.product_id,
        "product_name": product.product_name if product else None,
        "rating": row.rating,
        "review_text": row.review_text,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "rated_by_email": rated_by.email if rated_by else None,
        "image_urls": [_build_review_image_url(img.file_path) for img in image_rows],
        "image_paths": [img.file_path for img in image_rows],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _build_review_image_url(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    return f"/api/v1/admin/procurement-review-images/{normalized}"


def _optional_trimmed_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _validate_supplier_fields(
    *,
    supplier_name: str,
    email: str | None,
    product_links: object,
    is_active: object,
    address_line1: str | None,
    address_line2: str | None,
    address_line3: str | None,
    phone_number: str | None,
) -> str | None:
    if not supplier_name:
        return "supplier_name is required"
    if len(supplier_name) > 250:
        return "supplier_name exceeds max length 250"
    if email and len(email) > 255:
        return "email exceeds max length 255"
    if address_line1 and len(address_line1) > 100:
        return "address_line1 exceeds max length 100"
    if address_line2 and len(address_line2) > 100:
        return "address_line2 exceeds max length 100"
    if address_line3 and len(address_line3) > 100:
        return "address_line3 exceeds max length 100"
    if phone_number and len(phone_number) > 12:
        return "phone_number exceeds max length 12"
    if not isinstance(is_active, bool):
        return "is_active must be boolean"
    if not isinstance(product_links, list) or not product_links:
        return "product_links must be a non-empty list"
    for link in product_links:
        if not isinstance(link, dict):
            return "each product_link must be object with product_id and supplier_type"
        if not isinstance(link.get("product_id"), int):
            return "product_link.product_id must be integer"
        supplier_type = str(link.get("supplier_type", "")).strip().lower()
        if supplier_type not in {"primary", "secondary", "reseller"}:
            return "product_link.supplier_type must be one of primary, secondary, reseller"
    return None


def _normalize_supplier_product_links(product_links: list[dict[str, object]]) -> list[dict[str, object]]:
    dedup: dict[int, str] = {}
    for link in product_links:
        product_id = int(link["product_id"])
        supplier_type = str(link.get("supplier_type", "")).strip().lower()
        dedup[product_id] = supplier_type
    return [
        {"product_id": product_id, "supplier_type": dedup[product_id]}
        for product_id in sorted(dedup.keys())
    ]


def _save_procurement_review_image(file_storage, review_id: int) -> tuple[str | None, str | None]:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None, "invalid image filename"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return None, "only .jpg, .jpeg, .png, .webp, .gif images are allowed"

    images_root = os.path.join(current_app.instance_path, "uploads", "procurement_reviews")
    review_dir = os.path.join(images_root, str(review_id))
    os.makedirs(review_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(review_dir, stored_name)
    file_storage.save(abs_path)
    relative_path = f"{review_id}/{stored_name}"
    return relative_path, None


def _build_user_row(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "roles": sorted(role.name for role in user.roles),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "region": user.region,
        "source_region_id": user.source_region_id,
        "major_distribution_region_id": user.major_distribution_region_id,
        "seller_status": user.seller_status,
        "assigned_admin_user_id": user.assigned_admin_user_id,
    }


def _owned_distribution_regions_for_ambassador(ambassador_user_id: int) -> list[Region]:
    regions = (
        db.session.query(Region)
        .join(RegionDefault, RegionDefault.region_id == Region.region_id)
        .filter(
            Region.region_type == "distribution",
            RegionDefault.default_ambassador_user_id == ambassador_user_id,
        )
        .all()
    )
    return sorted(regions, key=lambda r: (_level_rank(r.distribution_level), r.region_id))


def _level_rank(level: str | None) -> int:
    if level == "major":
        return 1
    if level == "minor":
        return 2
    if level == "local":
        return 3
    return 9


def _major_region_id(region: Region) -> int | None:
    if region.region_type != "distribution":
        return None
    if region.distribution_level == "major":
        return region.region_id
    if region.distribution_level == "minor":
        return region.parent_region_id
    if region.distribution_level == "local":
        if region.parent_region_id is None:
            return None
        minor = db.session.get(Region, region.parent_region_id)
        if minor is None:
            return None
        return minor.parent_region_id
    return None


def _scope_user_ids_for_region(region: Region, current_ambassador_user_id: int) -> tuple[set[int], set[int]]:
    if region.distribution_level == "major":
        major_id = region.region_id
        subtree_ids = _distribution_subtree_region_ids_for_major(major_id)
        ambassador_ids = set(
            row[0]
            for row in db.session.query(RegionDefault.default_ambassador_user_id)
            .filter(
                RegionDefault.region_id.in_(subtree_ids),
                RegionDefault.default_ambassador_user_id.isnot(None),
            )
            .all()
        )
        buyer_ids = set(
            row[0]
            for row in db.session.query(User.id)
            .filter(User.roles.any(name="buyer"), User.major_distribution_region_id == major_id)
            .all()
        )
        return ambassador_ids, buyer_ids

    if region.distribution_level == "minor":
        major_id = _major_region_id(region)
        if major_id is None:
            return set(), set()
        local_region_ids = _local_region_ids_under_minor(region.region_id)
        local_ambassador_ids = set(
            row[0]
            for row in db.session.query(RegionDefault.default_ambassador_user_id)
            .filter(
                RegionDefault.region_id.in_(local_region_ids),
                RegionDefault.default_ambassador_user_id.isnot(None),
            )
            .all()
        )
        buyer_ids_in_major = set(
            row[0]
            for row in db.session.query(User.id)
            .filter(User.roles.any(name="buyer"), User.major_distribution_region_id == major_id)
            .all()
        )
        buyers_assigned_to_local = set()
        if local_ambassador_ids:
            buyers_assigned_to_local = set(
                row[0]
                for row in db.session.query(AmbassadorBuyerAssignment.buyer_user_id)
                .filter(AmbassadorBuyerAssignment.ambassador_user_id.in_(local_ambassador_ids))
                .all()
            )
        available_buyer_ids = buyer_ids_in_major - buyers_assigned_to_local
        return local_ambassador_ids, available_buyer_ids

    if region.distribution_level == "local":
        major_id = _major_region_id(region)
        if major_id is None:
            return {current_ambassador_user_id}, set()
        buyer_ids = set(
            row[0]
            for row in db.session.query(AmbassadorBuyerAssignment.buyer_user_id)
            .filter(AmbassadorBuyerAssignment.ambassador_user_id == current_ambassador_user_id)
            .all()
        )
        return {current_ambassador_user_id}, buyer_ids

    return set(), set()


def _allowed_group_scope_for_ambassador(ambassador_user_id: int) -> tuple[set[int], set[int]]:
    owned_regions = _owned_distribution_regions_for_ambassador(ambassador_user_id)
    allowed_ambassador_ids: set[int] = set()
    allowed_buyer_ids: set[int] = set()
    for region in owned_regions:
        ambassadors, buyers = _scope_user_ids_for_region(region, ambassador_user_id)
        allowed_ambassador_ids.update(ambassadors)
        allowed_buyer_ids.update(buyers)
    if not allowed_ambassador_ids:
        allowed_ambassador_ids.add(ambassador_user_id)
    return allowed_ambassador_ids, allowed_buyer_ids


def _distribution_subtree_region_ids_for_major(major_region_id: int) -> set[int]:
    minor_ids = [
        row[0]
        for row in db.session.query(Region.region_id)
        .filter(
            Region.region_type == "distribution",
            Region.distribution_level == "minor",
            Region.parent_region_id == major_region_id,
        )
        .all()
    ]
    local_ids = _local_region_ids_under_minor_ids(minor_ids)
    return {major_region_id, *minor_ids, *local_ids}


def _local_region_ids_under_minor(minor_region_id: int) -> list[int]:
    return _local_region_ids_under_minor_ids([minor_region_id])


def _local_region_ids_under_minor_ids(minor_region_ids: list[int]) -> list[int]:
    if not minor_region_ids:
        return []
    return [
        row[0]
        for row in db.session.query(Region.region_id)
        .filter(
            Region.region_type == "distribution",
            Region.distribution_level == "local",
            Region.parent_region_id.in_(minor_region_ids),
        )
        .all()
    ]


def _validate_product_fields(
    product_name: str,
    product_type: str,
    product_unit: str,
    validity_days: object,
) -> str | None:
    if not product_name or not product_type or not product_unit:
        return "product_name, product_type, and product_unit are required"
    if not isinstance(validity_days, int):
        return "validity_days must be integer"
    if validity_days < 1:
        return "validity_days must be at least 1"
    if validity_days > 36500:
        return "validity_days exceeds max 36500"
    if len(product_name) > 100:
        return "product_name exceeds max length 100"
    if len(product_type) > 50:
        return "product_type exceeds max length 50"
    if len(product_unit) > 10:
        return "product_unit exceeds max length 10"
    if _canonical_product_type(product_type) is None:
        return "invalid product_type; choose one from product_types"
    return None


def _canonical_product_type(product_type: str) -> str | None:
    exact_row = db.session.query(ProductType.product_type).filter(ProductType.product_type == product_type).first()
    if exact_row:
        return exact_row[0]
    row = (
        db.session.query(ProductType.product_type)
        .filter(db.func.lower(ProductType.product_type) == product_type.lower())
        .order_by(ProductType.id.asc())
        .first()
    )
    return row[0] if row else None


def _build_inventory_item_response(
    item: InventoryItem | FreshProduceInventoryItem,
    *,
    inventory_kind: str = "regular",
) -> dict[str, object]:
    is_expired = _is_inventory_item_expired(item)
    stored_quantity = item.quantity if inventory_kind == "regular" else item.estimated_quantity
    effective_quantity = 0 if is_expired else stored_quantity
    if item.origin_type == "procurement":
        status = "active" if (item.supplier and item.supplier.is_active) else "inactive"
    else:
        status = item.seller.seller_status if item.seller else None
    return {
        "id": item.id,
        "inventory_kind": inventory_kind,
        "product_id": item.product_id,
        "product_name": item.product.product_name if item.product else None,
        "product_type": item.product.product_type if item.product else None,
        "product_unit": item.product.product_unit if item.product else None,
        "product_validity_days": item.product.validity_days if item.product else None,
        "seller_id": item.seller_id,
        "seller_email": item.seller.email if item.seller else None,
        "seller_status": status,
        "supplier_id": item.supplier_id,
        "supplier_name": item.supplier.supplier_name if item.supplier else None,
        "supplier_email": item.supplier.email if item.supplier else None,
        "origin_type": item.origin_type,
        "origin": item.origin,
        "entry_date": item.entry_date.isoformat() if item.entry_date else None,
        "quantity": effective_quantity,
        "estimated_quantity": stored_quantity if inventory_kind == "fresh_produce" else None,
        "stored_quantity": stored_quantity,
        "is_expired": is_expired,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "created_by_admin_user_id": item.created_by_admin_user_id,
    }


def _is_inventory_item_expired(item: InventoryItem | FreshProduceInventoryItem) -> bool:
    if item.product is None or item.product.validity_days is None:
        return False
    updated_at = item.updated_at
    if updated_at is None:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    expiry_at = updated_at + timedelta(days=item.product.validity_days)
    return datetime.now(timezone.utc) >= expiry_at


def _validate_region_fields(
    region_name: str,
    region_description: str | None,
    region_type: str,
) -> str | None:
    if not region_name:
        return "region_name is required"
    if len(region_name) > 150:
        return "region_name exceeds max length 150"
    if region_description and len(region_description) > 1500:
        return "region_description exceeds max length 1500"
    if region_type not in {"source", "distribution"}:
        return "region_type must be source or distribution"
    return None


def _validate_distribution_hierarchy(
    *,
    region_type: str,
    distribution_level: str | None,
    parent_region_id: object,
) -> str | None:
    if region_type == "source":
        if distribution_level is not None:
            return "distribution_level must be empty for source regions"
        if parent_region_id is not None:
            return "parent_region_id must be empty for source regions"
        return None

    if distribution_level not in {"major", "minor", "local"}:
        return "distribution_level must be one of major, minor, local for distribution regions"

    if distribution_level == "major":
        if parent_region_id is not None:
            return "major distribution regions cannot have a parent_region_id"
        return None

    if not isinstance(parent_region_id, int):
        return "parent_region_id is required for minor/local distribution regions"

    parent = db.session.get(Region, parent_region_id)
    if parent is None:
        return "parent region not found"
    if parent.region_type != "distribution":
        return "parent region must be distribution type"

    if distribution_level == "minor":
        if parent.distribution_level != "major":
            return "minor distribution region parent must be a major distribution region"
    if distribution_level == "local":
        if parent.distribution_level != "minor":
            return "local distribution region parent must be a minor distribution region"

    return None


def _int_query_arg(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if minimum is not None and value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _optional_int_query_arg(name: str) -> int | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
