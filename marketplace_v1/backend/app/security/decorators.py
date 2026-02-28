from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def _missing_claims_response() -> tuple[dict[str, str], int]:
    return {"message": "Forbidden"}, 403


def require_roles(*required_roles: str) -> Callable[..., Any]:
    required_set = set(required_roles)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            verify_jwt_in_request()
            claims = get_jwt()
            roles = set(claims.get("roles", []))

            if not required_set.issubset(roles):
                body, status = _missing_claims_response()
                return jsonify(body), status

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_permissions(*required_permissions: str) -> Callable[..., Any]:
    required_set = set(required_permissions)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            verify_jwt_in_request()
            claims = get_jwt()
            permissions = set(claims.get("permissions", []))

            if not required_set.issubset(permissions):
                body, status = _missing_claims_response()
                return jsonify(body), status

            return func(*args, **kwargs)

        return wrapper

    return decorator
