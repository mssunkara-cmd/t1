from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.extensions import db
from app.models import FreshProduceInventoryItem, InventoryItem, Order, OrderGroup, OrderItem, Product, Supplier, User
from app.security.decorators import require_permissions
from app.services.auth_service import list_buyers_for_ambassador

order_bp = Blueprint("orders", __name__)


@order_bp.get("/ping")
def ping_orders() -> tuple[dict[str, str], int]:
    return {"message": "order route ready"}, 200


@order_bp.get("")
@require_permissions("order.read")
def list_orders() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    claims = get_jwt()
    roles = set(claims.get("roles", []))

    query = db.session.query(Order)
    if not roles.intersection({"admin", "super_admin", "support_ops"}):
        query = query.filter((Order.buyer_id == current_user_id) | (Order.seller_id == current_user_id))

    orders = query.order_by(Order.created_at.desc()).limit(200).all()
    return {
        "items": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "order_group_id": order.order_group_id,
                "group_number": order.order_group.group_number if order.order_group else None,
                "buyer_id": order.buyer_id,
                "seller_id": order.seller_id,
                "supplier_id": order.supplier_id,
                "seller_name": _user_display_name(order.seller),
                "supplier_name": order.supplier.supplier_name if order.supplier else None,
                "source_label": _order_source_label(order),
                "status": order.status,
                "total_amount": str(order.total_amount),
                "currency": order.currency,
                "items": [
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "product_id": item.product_id,
                        "inventory_kind": item.inventory_kind,
                        "source_inventory_item_id": item.source_inventory_item_id,
                        "qty": item.qty,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
            }
            for order in orders
        ]
    }, 200


@order_bp.get("/groups")
@require_permissions("order.read")
def list_order_groups() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    claims = get_jwt()
    roles = set(claims.get("roles", []))

    query = db.session.query(OrderGroup)
    if not roles.intersection({"admin", "super_admin", "support_ops"}):
        query = query.filter(OrderGroup.buyer_id == current_user_id)

    groups = query.order_by(OrderGroup.created_at.desc(), OrderGroup.id.desc()).limit(200).all()
    return {"items": [_build_order_group_response(group) for group in groups]}, 200


@order_bp.get("/groups/<int:order_group_id>")
@require_permissions("order.read")
def get_order_group(order_group_id: int) -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    claims = get_jwt()
    roles = set(claims.get("roles", []))

    group = db.session.get(OrderGroup, order_group_id)
    if group is None:
        return {"message": "order group not found"}, 404

    if not roles.intersection({"admin", "super_admin", "support_ops"}) and group.buyer_id != current_user_id:
        return {"message": "Forbidden"}, 403

    return _build_order_group_response(group), 200


@order_bp.get("/ambassador-groups")
@require_permissions("buyer.group.read")
def list_ambassador_buyer_order_groups() -> tuple[dict[str, list[dict[str, object]]], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    buyer_ids = [buyer.id for buyer in list_buyers_for_ambassador(current_user_id)]
    if not buyer_ids:
        return {"items": []}, 200

    groups = (
        db.session.query(OrderGroup)
        .filter(OrderGroup.buyer_id.in_(buyer_ids))
        .order_by(OrderGroup.created_at.desc(), OrderGroup.id.desc())
        .limit(300)
        .all()
    )
    return {"items": [_build_order_group_response(group) for group in groups]}, 200


@order_bp.get("/catalog")
@require_permissions("order.create")
def search_order_catalog() -> tuple[dict[str, list[dict[str, object]]], int]:
    product_type = str(request.args.get("product_type", "")).strip()
    product_name = str(request.args.get("product_name", "")).strip()
    seller_name = str(request.args.get("seller_name", "")).strip()
    supplier_name = str(request.args.get("supplier_name", "")).strip()

    def _base_rows(model_cls: type[InventoryItem] | type[FreshProduceInventoryItem], inventory_kind: str):
        query = (
            db.session.query(model_cls, Product, User, Supplier)
            .join(Product, model_cls.product_id == Product.id)
            .outerjoin(User, model_cls.seller_id == User.id)
            .outerjoin(Supplier, model_cls.supplier_id == Supplier.supplier_id)
        )
        if product_type:
            query = query.filter(Product.product_type.ilike(f"%{product_type}%"))
        if product_name:
            query = query.filter(Product.product_name.ilike(f"%{product_name}%"))
        if seller_name:
            query = query.filter(
                (User.email.ilike(f"%{seller_name}%"))
                | (User.first_name.ilike(f"%{seller_name}%"))
                | (User.last_name.ilike(f"%{seller_name}%"))
            )
        if supplier_name:
            query = query.filter(Supplier.supplier_name.ilike(f"%{supplier_name}%"))

        rows = query.limit(500).all()
        result: list[dict[str, object]] = []
        for item, product, seller, supplier in rows:
            available_quantity = _available_inventory_quantity(item, product, inventory_kind=inventory_kind)
            if available_quantity <= 0:
                continue
            can_order = bool(
                (seller and seller.seller_status == "valid" and any(role.name == "seller" for role in seller.roles))
                or (supplier and supplier.is_active)
            )
            result.append(
                {
                    "inventory_kind": inventory_kind,
                    "inventory_item_id": item.id,
                    "product_id": product.id,
                    "product_name": product.product_name,
                    "product_type": product.product_type,
                    "product_unit": product.product_unit,
                    "seller_id": seller.id if seller else None,
                    "seller_name": _user_display_name(seller),
                    "supplier_id": supplier.supplier_id if supplier else None,
                    "supplier_name": supplier.supplier_name if supplier else None,
                    "available_quantity": available_quantity,
                    "source_label": _catalog_source_label(seller=seller, supplier=supplier),
                    "suggested_unit_price": str(item.price_per_unit) if item.price_per_unit is not None else None,
                    "can_order": can_order,
                }
            )
        return result

    rows = _base_rows(InventoryItem, "regular") + _base_rows(FreshProduceInventoryItem, "fresh_produce")
    rows.sort(key=lambda row: (str(row.get("product_name", "")).lower(), -int(row.get("available_quantity", 0))))
    return {"items": rows[:500]}, 200


@order_bp.post("")
@require_permissions("order.create")
def create_order() -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    payload = request.get_json(silent=True) or {}
    seller_id = payload.get("seller_id")
    supplier_id = payload.get("supplier_id")
    currency = str(payload.get("currency", "USD")).upper()
    items_payload = payload.get("items")

    if not isinstance(items_payload, list) or not items_payload:
        return {"message": "items must be a non-empty list"}, 400

    source_groups: dict[tuple[str, int], dict[str, object]] = {}
    total = Decimal("0")
    for idx, item in enumerate(items_payload):
        if not isinstance(item, dict):
            return {"message": f"item at index {idx} must be an object"}, 400

        item_seller_id = item.get("seller_id", seller_id)
        item_supplier_id = item.get("supplier_id", supplier_id)
        sku = str(item.get("sku", "")).strip()
        name = str(item.get("name", "")).strip()
        product_id = item.get("product_id")
        inventory_kind = str(item.get("inventory_kind", "")).strip().lower()
        source_inventory_item_id = item.get("source_inventory_item_id")
        qty_raw = item.get("qty")
        unit_price_raw = item.get("unit_price")

        if not sku or not name:
            return {"message": f"item at index {idx} requires sku and name"}, 400
        if not isinstance(product_id, int):
            return {"message": f"item at index {idx} requires product_id"}, 400
        if inventory_kind not in {"regular", "fresh_produce"}:
            return {"message": f"item at index {idx} inventory_kind must be regular or fresh_produce"}, 400
        if not isinstance(source_inventory_item_id, int):
            return {"message": f"item at index {idx} requires source_inventory_item_id"}, 400
        if not isinstance(qty_raw, int) or qty_raw <= 0:
            return {"message": f"item at index {idx} qty must be a positive integer"}, 400

        try:
            unit_price = Decimal(str(unit_price_raw))
        except (InvalidOperation, TypeError, ValueError):
            return {"message": f"item at index {idx} unit_price is invalid"}, 400

        if unit_price <= 0:
            return {"message": f"item at index {idx} unit_price must be positive"}, 400

        if isinstance(item_seller_id, int) and isinstance(item_supplier_id, int):
            return {"message": f"item at index {idx} cannot have both seller_id and supplier_id"}, 400
        if not isinstance(item_seller_id, int) and not isinstance(item_supplier_id, int):
            return {"message": f"item at index {idx} requires seller_id or supplier_id"}, 400

        seller = None
        supplier = None
        if isinstance(item_seller_id, int):
            seller = db.session.get(User, item_seller_id)
            if seller is None:
                return {"message": f"item at index {idx} seller not found"}, 404
            seller_roles = {role.name for role in seller.roles}
            if "seller" not in seller_roles:
                return {"message": f"item at index {idx} seller_id does not belong to a seller user"}, 400
            if seller.seller_status != "valid":
                return {"message": f"item at index {idx} selected seller is not validated yet"}, 400
            source_key = ("seller", seller.id)
        else:
            supplier = db.session.get(Supplier, item_supplier_id)
            if supplier is None:
                return {"message": f"item at index {idx} supplier not found"}, 404
            if not supplier.is_active:
                return {"message": f"item at index {idx} selected supplier is inactive"}, 400
            source_key = ("supplier", supplier.supplier_id)

        inventory_model = InventoryItem if inventory_kind == "regular" else FreshProduceInventoryItem
        inventory_item = db.session.get(inventory_model, source_inventory_item_id)
        if inventory_item is None:
            return {"message": f"item at index {idx} inventory source not found"}, 404
        if inventory_item.product_id != product_id:
            return {"message": f"item at index {idx} product does not match inventory source"}, 400
        if _inventory_is_expired(inventory_item, inventory_item.product):
            return {"message": f"item at index {idx} inventory is expired"}, 400

        available_quantity = _available_inventory_quantity(inventory_item, inventory_item.product, inventory_kind=inventory_kind)
        if qty_raw > available_quantity:
            return {"message": f"item at index {idx} quantity exceeds available inventory"}, 400

        if seller is not None and inventory_item.seller_id != seller.id:
            return {"message": f"item at index {idx} inventory does not belong to selected seller"}, 400
        if supplier is not None and inventory_item.supplier_id != supplier.supplier_id:
            return {"message": f"item at index {idx} inventory does not belong to selected supplier"}, 400

        grouped = source_groups.setdefault(
            source_key,
            {
                "seller": seller,
                "supplier": supplier,
                "items": [],
                "total": Decimal("0"),
            },
        )
        grouped["items"].append(
            OrderItem(
                sku=sku,
                name=name,
                product_id=product_id,
                inventory_kind=inventory_kind,
                source_inventory_item_id=source_inventory_item_id,
                qty=qty_raw,
                unit_price=unit_price.quantize(Decimal("0.01")),
            )
        )
        grouped["total"] += unit_price * qty_raw
        inventory_item.reserved_quantity += qty_raw
        total += unit_price * qty_raw

    group_number = f"GRP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    order_group = OrderGroup(
        group_number=group_number,
        buyer_id=current_user_id,
        total_amount=total.quantize(Decimal("0.01")),
        currency=currency,
    )
    db.session.add(order_group)

    created_orders: list[Order] = []
    for index, grouped in enumerate(source_groups.values(), start=1):
        order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}-{index}"
        order = Order(
            order_number=order_number,
            order_group=order_group,
            buyer_id=current_user_id,
            seller_id=grouped["seller"].id if grouped["seller"] else None,
            supplier_id=grouped["supplier"].supplier_id if grouped["supplier"] else None,
            status="created",
            total_amount=grouped["total"].quantize(Decimal("0.01")),
            currency=currency,
        )
        order.items = grouped["items"]
        db.session.add(order)
        created_orders.append(order)

    db.session.commit()
    db.session.refresh(order_group)
    for order in created_orders:
        db.session.refresh(order)

    return {
        "order_group_id": order_group.id,
        "group_number": order_group.group_number,
        "total_amount": str(order_group.total_amount),
        "currency": order_group.currency,
        "orders": [_build_order_response(order) for order in created_orders],
    }, 201


@order_bp.patch("/<int:order_id>/status")
@require_permissions("order.status.update")
def update_order_status(order_id: int) -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    new_status = str(payload.get("status", "")).strip().lower()
    allowed_statuses = {"created", "confirmed", "packed", "shipped", "delivered", "cancelled"}

    if new_status not in allowed_statuses:
        return {"message": "invalid status"}, 400

    order = db.session.get(Order, order_id)
    if order is None:
        return {"message": "order not found"}, 404

    old_status = order.status
    if old_status in {"delivered", "cancelled"} and new_status != old_status:
        return {"message": "cannot change status once order is delivered or cancelled"}, 409

    if old_status != new_status and new_status in {"delivered", "cancelled"}:
        for item in order.items:
            inventory_model = InventoryItem if item.inventory_kind == "regular" else FreshProduceInventoryItem
            if item.source_inventory_item_id is None:
                continue
            inventory_item = db.session.get(inventory_model, item.source_inventory_item_id)
            if inventory_item is None:
                continue
            inventory_item.reserved_quantity = max(0, inventory_item.reserved_quantity - item.qty)
            if new_status == "delivered":
                if item.inventory_kind == "regular":
                    inventory_item.quantity = max(0, inventory_item.quantity - item.qty)
                else:
                    inventory_item.estimated_quantity = max(0, inventory_item.estimated_quantity - item.qty)

    order.status = new_status
    db.session.commit()

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
    }, 200


def _current_user_id_from_token() -> int | None:
    raw_identity = get_jwt_identity()
    try:
        return int(raw_identity)
    except (TypeError, ValueError):
        return None


def _build_order_response(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "order_group_id": order.order_group_id,
        "group_number": order.order_group.group_number if order.order_group else None,
        "buyer_id": order.buyer_id,
        "seller_id": order.seller_id,
        "supplier_id": order.supplier_id,
        "seller_name": _user_display_name(order.seller),
        "supplier_name": order.supplier.supplier_name if order.supplier else None,
        "source_label": _order_source_label(order),
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "items": [
            {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "product_id": item.product_id,
                "inventory_kind": item.inventory_kind,
                "source_inventory_item_id": item.source_inventory_item_id,
                "qty": item.qty,
                "unit_price": str(item.unit_price),
            }
            for item in order.items
        ],
    }


def _build_order_group_response(group: OrderGroup) -> dict[str, object]:
    buyer = group.buyer
    return {
        "order_group_id": group.id,
        "group_number": group.group_number,
        "buyer_id": group.buyer_id,
        "buyer_email": buyer.email if buyer else None,
        "buyer_name": _user_display_name(buyer),
        "total_amount": str(group.total_amount),
        "currency": group.currency,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "orders": [_build_order_response(order) for order in sorted(group.orders, key=lambda row: row.id)],
    }


def _inventory_is_expired(item: InventoryItem | FreshProduceInventoryItem, product: Product) -> bool:
    if product.validity_days is None:
        return False
    updated_at = item.updated_at
    if updated_at is None:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= (updated_at + timedelta(days=product.validity_days))


def _available_inventory_quantity(
    item: InventoryItem | FreshProduceInventoryItem,
    product: Product | None,
    *,
    inventory_kind: str,
) -> int:
    if product is not None and _inventory_is_expired(item, product):
        return 0
    base = item.quantity if inventory_kind == "regular" else item.estimated_quantity
    return max(0, base - getattr(item, "reserved_quantity", 0))


def _user_display_name(user: User | None) -> str | None:
    if user is None:
        return None
    full = " ".join([part for part in [user.first_name, user.last_name] if part]).strip()
    if full:
        return full
    return user.email


def _catalog_source_label(*, seller: User | None, supplier: Supplier | None) -> str:
    if seller is not None:
        return f"Seller: {_user_display_name(seller) or seller.id}"
    if supplier is not None:
        return f"Supplier: {supplier.supplier_name}"
    return "Unknown"


def _order_source_label(order: Order) -> str:
    if order.seller is not None:
        return f"Seller: {_user_display_name(order.seller) or order.seller_id}"
    if order.supplier is not None:
        return f"Supplier: {order.supplier.supplier_name}"
    return "Unknown"
