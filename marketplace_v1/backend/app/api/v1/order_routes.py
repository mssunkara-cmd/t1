from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.extensions import db
from app.models import Order, OrderItem, User
from app.security.decorators import require_permissions

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
                "buyer_id": order.buyer_id,
                "seller_id": order.seller_id,
                "status": order.status,
                "total_amount": str(order.total_amount),
                "currency": order.currency,
                "items": [
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "qty": item.qty,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
            }
            for order in orders
        ]
    }, 200


@order_bp.post("")
@require_permissions("order.create")
def create_order() -> tuple[dict[str, object], int]:
    current_user_id = _current_user_id_from_token()
    if current_user_id is None:
        return {"message": "invalid token identity"}, 401

    payload = request.get_json(silent=True) or {}
    seller_id = payload.get("seller_id")
    currency = str(payload.get("currency", "USD")).upper()
    items_payload = payload.get("items")

    if not isinstance(seller_id, int):
        return {"message": "seller_id must be an integer"}, 400

    seller = db.session.get(User, seller_id)
    if seller is None:
        return {"message": "seller not found"}, 404
    seller_roles = {role.name for role in seller.roles}
    if "seller" not in seller_roles:
        return {"message": "seller_id does not belong to a seller user"}, 400
    if seller.seller_status != "valid":
        return {"message": "selected seller is not validated yet"}, 400

    if not isinstance(items_payload, list) or not items_payload:
        return {"message": "items must be a non-empty list"}, 400

    parsed_items: list[OrderItem] = []
    total = Decimal("0")
    for idx, item in enumerate(items_payload):
        if not isinstance(item, dict):
            return {"message": f"item at index {idx} must be an object"}, 400

        sku = str(item.get("sku", "")).strip()
        name = str(item.get("name", "")).strip()
        qty_raw = item.get("qty")
        unit_price_raw = item.get("unit_price")

        if not sku or not name:
            return {"message": f"item at index {idx} requires sku and name"}, 400
        if not isinstance(qty_raw, int) or qty_raw <= 0:
            return {"message": f"item at index {idx} qty must be a positive integer"}, 400

        try:
            unit_price = Decimal(str(unit_price_raw))
        except (InvalidOperation, TypeError, ValueError):
            return {"message": f"item at index {idx} unit_price is invalid"}, 400

        if unit_price <= 0:
            return {"message": f"item at index {idx} unit_price must be positive"}, 400

        parsed_items.append(
            OrderItem(sku=sku, name=name, qty=qty_raw, unit_price=unit_price.quantize(Decimal("0.01")))
        )
        total += unit_price * qty_raw

    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    order = Order(
        order_number=order_number,
        buyer_id=current_user_id,
        seller_id=seller_id,
        status="created",
        total_amount=total.quantize(Decimal("0.01")),
        currency=currency,
    )
    order.items = parsed_items

    db.session.add(order)
    db.session.commit()
    db.session.refresh(order)

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
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
