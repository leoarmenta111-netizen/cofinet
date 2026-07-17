from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_token
from app.database.deps import get_db
from app.models.admin import Admin


def get_current_active_admin(
    token_payload: dict[str, object] = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> Admin:
    """Resolve an active administrator from an admin-scoped JWT."""
    if token_payload.get("role") != "admin":
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
