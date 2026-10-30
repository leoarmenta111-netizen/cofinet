from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from app.auth.admin_security import (
    require_super_admin,
)
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.pos_staff import (
    AdminPosStaffCreate,
    AdminPosStaffResetPin,
    AdminPosStaffResponse,
    AdminPosStaffUpdate,
)
from app.services.pos_staff_service import (
    PosStaffService,
)


router = APIRouter(
    prefix="/admin/pos/staff",
    tags=["Admin POS Staff"],
)


@router.get(
    "",
    response_model=list[AdminPosStaffResponse],
)
def list_pos_staff(
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    rows = PosStaffService.list_staff(db)

    return [
        AdminPosStaffResponse(
            id=staff.id,
            branch_id=staff.branch_id,
            branch_code=branch.code,
            display_name=staff.display_name,
            role=staff.role,
            is_active=staff.is_active,
        )
        for staff, branch in rows
    ]


@router.post(
    "",
    response_model=AdminPosStaffResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pos_staff(
    data: AdminPosStaffCreate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    staff, branch = (
        PosStaffService.create_staff(
            db,
            branch_id=data.branch_id,
            display_name=data.display_name,
            role=data.role,
            pin=data.pin,
        )
    )

    return AdminPosStaffResponse(
        id=staff.id,
        branch_id=staff.branch_id,
        branch_code=branch.code,
        display_name=staff.display_name,
        role=staff.role,
        is_active=staff.is_active,
    )



@router.patch(
    "/{staff_id}",
    response_model=AdminPosStaffResponse,
)
def update_pos_staff(
    staff_id: int,
    data: AdminPosStaffUpdate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    staff, branch = (
        PosStaffService.update_staff(
            db,
            staff_id=staff_id,
            display_name=data.display_name,
            role=data.role,
            is_active=data.is_active,
        )
    )

    return AdminPosStaffResponse(
        id=staff.id,
        branch_id=staff.branch_id,
        branch_code=branch.code,
        display_name=staff.display_name,
        role=staff.role,
        is_active=staff.is_active,
    )



@router.post(
    "/{staff_id}/reset-pin",
    response_model=AdminPosStaffResponse,
)
def reset_pos_staff_pin(
    staff_id: int,
    data: AdminPosStaffResetPin,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    staff, branch = (
        PosStaffService.reset_pin(
            db,
            staff_id=staff_id,
            pin=data.pin,
        )
    )

    return AdminPosStaffResponse(
        id=staff.id,
        branch_id=staff.branch_id,
        branch_code=branch.code,
        display_name=staff.display_name,
        role=staff.role,
        is_active=staff.is_active,
    )
