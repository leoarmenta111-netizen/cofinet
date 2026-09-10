from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_token
from app.database.deps import get_db
from app.models.admin import Admin, AdminRole


def get_current_active_admin(
    token_payload: dict[str, object] = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> Admin:
    """Resolve an active administrator from an admin-scoped JWT."""
    if token_payload.get("role") != "admin" and token_payload.get("scope") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    try:
        admin_id = int(token_payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

    admin = db.get(Admin, admin_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive admin")
    return admin


def require_admin_roles(*allowed_roles: AdminRole):
    """Build a reusable dependency that enforces one or more administrator roles."""
    allowed = frozenset(allowed_roles)

    def dependency(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
        if current_admin.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_admin

    return dependency


require_super_admin = require_admin_roles(AdminRole.SUPER_ADMIN)
require_pin_access = require_admin_roles(AdminRole.SUPER_ADMIN, AdminRole.PIN_OPERATOR)
