from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.services.branch_service import BranchService


class PosStaffService:
    @staticmethod
    def verify_pin(
        db: Session,
        *,
        staff_id: int,
        pin: str,
        branch_code: str,
    ) -> PosStaff:
        branch = BranchService.get_by_code(
            db,
            branch_code,
        )

        staff = db.get(
            PosStaff,
            staff_id,
        )

        if (
            staff is None
            or staff.branch_id != branch.id
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff credentials",
            )

        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive POS staff",
            )

        if not verify_password(
            pin,
            staff.pin_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff credentials",
            )

        return staff

    @classmethod
    def authorize_manager(
        cls,
        db: Session,
        *,
        staff_id: int,
        pin: str,
        branch_code: str,
    ) -> PosStaff:
        staff = cls.verify_pin(
            db,
            staff_id=staff_id,
            pin=pin,
            branch_code=branch_code,
        )

        role = (
            staff.role.value
            if isinstance(staff.role, PosStaffRole)
            else staff.role
        )

        if role != PosStaffRole.MANAGER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager authorization required",
            )

        return staff
