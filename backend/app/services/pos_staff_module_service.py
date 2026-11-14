from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.operational_module import (
    OperationalModule,
    operational_module_value,
)
from app.models.pos_staff import PosStaff
from app.models.pos_staff_module import PosStaffModule


class PosStaffModuleService:
    @staticmethod
    def modules_for_staff(
        db: Session,
        *,
        staff_id: int,
    ) -> list[str]:
        return list(
            db.execute(
                select(
                    PosStaffModule.module_code
                ).where(
                    PosStaffModule.staff_id
                    == staff_id
                )
            ).scalars().all()
        )

    @classmethod
    def has_access(
        cls,
        db: Session,
        *,
        staff: PosStaff,
        module_code: OperationalModule | str,
    ) -> bool:
        expected = operational_module_value(
            module_code
        )

        modules = cls.modules_for_staff(
            db,
            staff_id=staff.id,
        )

        # Compatibility fallback for records/tests
        # created before the permission table existed.
        if not modules:
            return staff.module_code == expected

        return expected in modules

    @classmethod
    def require_access(
        cls,
        db: Session,
        *,
        staff: PosStaff,
        module_code: OperationalModule | str,
    ) -> None:
        if not cls.has_access(
            db,
            staff=staff,
            module_code=module_code,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="POS staff module mismatch",
            )

    @staticmethod
    def grant_access(
        db: Session,
        *,
        staff: PosStaff,
        module_code: OperationalModule | str,
    ) -> None:
        value = operational_module_value(
            module_code
        )

        existing = db.get(
            PosStaffModule,
            (staff.id, value),
        )

        if existing is None:
            db.add(
                PosStaffModule(
                    staff_id=staff.id,
                    module_code=value,
                )
            )
