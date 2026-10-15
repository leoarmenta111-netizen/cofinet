from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.models.branch import Branch
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.services.branch_service import BranchService


class PosStaffService:
    @staticmethod
    def create_staff(
        db: Session,
        *,
        branch_id: int,
        display_name: str,
        role: PosStaffRole,
        pin: str,
    ) -> tuple[PosStaff, Branch]:
        branch = db.get(
            Branch,
            branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        staff = PosStaff(
            branch_id=branch.id,
            display_name=display_name,
            role=role,
            pin_hash=hash_password(pin),
            is_active=True,
        )

        db.add(staff)
        db.commit()
        db.refresh(staff)

        return staff, branch

    @staticmethod
    def list_staff(
        db: Session,
    ) -> list[tuple[PosStaff, Branch]]:
        return list(
            db.execute(
                select(
                    PosStaff,
                    Branch,
                )
                .join(
                    Branch,
                    Branch.id == PosStaff.branch_id,
                )
                .order_by(PosStaff.id)
            ).all()
        )

    @staticmethod
    def update_staff(
        db: Session,
        *,
        staff_id: int,
        display_name: str | None = None,
        role: PosStaffRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[PosStaff, Branch]:
        staff = db.get(
            PosStaff,
            staff_id,
        )

        if staff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="POS staff not found",
            )

        if display_name is not None:
            staff.display_name = display_name

        if role is not None:
            staff.role = role

        if is_active is not None:
            staff.is_active = is_active

        branch = db.get(
            Branch,
            staff.branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        db.commit()
        db.refresh(staff)

        return staff, branch

    @staticmethod
    def reset_pin(
        db: Session,
        *,
        staff_id: int,
        pin: str,
    ) -> tuple[PosStaff, Branch]:
        staff = db.get(
            PosStaff,
            staff_id,
        )

        if staff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="POS staff not found",
            )

        branch = db.get(
            Branch,
            staff.branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        staff.pin_hash = hash_password(pin)

        db.commit()
        db.refresh(staff)

        return staff, branch

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
