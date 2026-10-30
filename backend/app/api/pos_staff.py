from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.pos_staff_security import (
    create_pos_staff_token,
    get_current_pos_staff,
)
from app.auth.security import get_current_token
from app.database.deps import get_db
from app.models.pos_staff import PosStaff, PosStaffRole
from app.schemas.pos_staff import (
    PosStaffSessionResponse,
    PosStaffUnlockRequest,
    PosStaffUnlockResponse,
)
from app.services.branch_service import BranchService
from app.services.pos_staff_service import PosStaffService


router = APIRouter(
    prefix="/pos/staff",
    tags=["POS Staff"],
)


@router.post(
    "/unlock",
    response_model=PosStaffUnlockResponse,
)
def unlock_pos_staff(
    payload: PosStaffUnlockRequest,
    db: Session = Depends(get_db),
) -> PosStaffUnlockResponse:
    staff = PosStaffService.verify_pin(
        db,
        staff_id=payload.staff_id,
        pin=payload.pin,
        branch_code=payload.branch_code,
    )

    branch = BranchService.get_by_id(
        db,
        staff.branch_id,
    )

    token = create_pos_staff_token(
        staff,
        branch_code=branch.code,
        terminal_id=payload.terminal_id,
    )

    role = (
        staff.role
        if isinstance(staff.role, PosStaffRole)
        else PosStaffRole(staff.role)
    )

    return PosStaffUnlockResponse(
        staff_id=staff.id,
        display_name=staff.display_name,
        role=role,
        branch_code=branch.code,
        terminal_id=payload.terminal_id,
        access_token=token,
    )



@router.get(
    "/session",
    response_model=PosStaffSessionResponse,
)
def get_pos_staff_session(
    current_staff: PosStaff = Depends(get_current_pos_staff),
    token_payload: dict[str, object] = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> PosStaffSessionResponse:
    branch = BranchService.get_by_id(
        db,
        current_staff.branch_id,
    )

    branch_code = token_payload.get("branch_code")
    terminal_id = token_payload.get("terminal_id")

    if (
        not isinstance(branch_code, str)
        or branch_code != branch.code
        or not isinstance(terminal_id, str)
        or not terminal_id.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    role = (
        current_staff.role
        if isinstance(current_staff.role, PosStaffRole)
        else PosStaffRole(current_staff.role)
    )

    return PosStaffSessionResponse(
        staff_id=current_staff.id,
        display_name=current_staff.display_name,
        role=role,
        branch_code=branch.code,
        terminal_id=terminal_id,
    )
