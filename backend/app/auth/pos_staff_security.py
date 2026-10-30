from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    get_current_token,
)
from app.database.deps import get_db
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)


def create_pos_staff_token(
    staff: PosStaff,
    *,
    branch_code: str,
    terminal_id: str,
) -> str:
    role = (
        staff.role.value
        if isinstance(staff.role, PosStaffRole)
        else staff.role
    )

    return create_access_token(
        {
            "sub": str(staff.id),
            "scope": "pos_staff",
            "role": role,
            "branch_id": staff.branch_id,
            "branch_code": branch_code,
            "terminal_id": terminal_id,
        }
    )


def get_current_pos_staff(
    token_payload: dict[str, object] = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> PosStaff:
    if token_payload.get("scope") != "pos_staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="POS staff access required",
        )

    try:
        staff_id = int(token_payload["sub"])
        token_branch_id = int(token_payload["branch_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

    staff = db.get(PosStaff, staff_id)

    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="POS staff not found",
        )

    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive POS staff",
        )

    if staff.branch_id != token_branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="POS staff branch mismatch",
        )

    return staff


def require_pos_manager(
    current_staff: PosStaff = Depends(get_current_pos_staff),
) -> PosStaff:
    role = (
        current_staff.role.value
        if isinstance(current_staff.role, PosStaffRole)
        else current_staff.role
    )

    if role != PosStaffRole.MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager authorization required",
        )

    return current_staff
