from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    get_current_token,
)
from app.database.deps import get_db
from app.domain.operational_module import (
    OperationalModule,
    operational_module_value,
)
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.services.pos_staff_module_service import (
    PosStaffModuleService,
)


def create_pos_staff_token(
    staff: PosStaff,
    *,
    branch_code: str,
    terminal_id: str,
    module_code: OperationalModule | str | None = None,
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
            "module_code": operational_module_value(
                module_code
                if module_code is not None
                else staff.module_code
            ),
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

    token_module = token_payload.get(
        "module_code",
        OperationalModule.CAFE.value,
    )

    PosStaffModuleService.require_access(
        db,
        staff=staff,
        module_code=token_module,
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
