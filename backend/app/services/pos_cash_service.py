from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_cash import (
    ACTIVE_SHIFT_STATUSES,
    PosCashDenominationCount,
    PosCashShift,
)
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.schemas.pos_cash import CashDenominationCount
from app.services.branch_service import BranchService
from app.services.pos_audit_service import PosAuditService


class PosCashService:
    @staticmethod
    def _staff_role(staff: PosStaff) -> str:
        if isinstance(staff.role, PosStaffRole):
            return staff.role.value

        return str(staff.role)

    @staticmethod
    def _validate_staff(
        *,
        staff: PosStaff,
        branch_id: int,
    ) -> None:
        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive POS staff",
            )

        if staff.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="POS staff branch mismatch",
            )

    @staticmethod
    def current_shift(
        db: Session,
        *,
        branch_code: str,
        terminal_id: str,
    ) -> PosCashShift | None:
        branch = BranchService.get_by_code(
            db,
            branch_code,
        )

        return db.execute(
            select(PosCashShift)
            .where(
                PosCashShift.branch_id == branch.id,
                PosCashShift.terminal_id == terminal_id,
                PosCashShift.status.in_(
                    ACTIVE_SHIFT_STATUSES
                ),
            )
            .order_by(PosCashShift.id.desc())
        ).scalar_one_or_none()

    @classmethod
    def open_shift(
        cls,
        db: Session,
        *,
        branch_code: str,
        terminal_id: str,
        opening_counts: list[CashDenominationCount],
        requesting_staff: PosStaff,
        authorizing_manager: PosStaff,
    ) -> PosCashShift:
        branch = BranchService.get_by_code(
            db,
            branch_code,
        )

        cls._validate_staff(
            staff=requesting_staff,
            branch_id=branch.id,
        )

        cls._validate_staff(
            staff=authorizing_manager,
            branch_id=branch.id,
        )

        if (
            cls._staff_role(authorizing_manager)
            != PosStaffRole.MANAGER.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager authorization required",
            )

        if not terminal_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Terminal ID is required",
            )

        if not opening_counts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Opening denomination count is required",
            )

        # Serialize opening attempts for this branch on databases
        # that support SELECT ... FOR UPDATE (PostgreSQL).
        db.execute(
            select(Branch)
            .where(Branch.id == branch.id)
            .with_for_update()
        ).scalar_one()

        existing = db.execute(
            select(PosCashShift)
            .where(
                PosCashShift.branch_id == branch.id,
                PosCashShift.terminal_id == terminal_id,
                PosCashShift.status.in_(
                    ACTIVE_SHIFT_STATUSES
                ),
            )
            .with_for_update()
        ).scalar_one_or_none()

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active cash shift already exists",
            )

        normalized_counts: dict[int, int] = {}

        for count in opening_counts:
            denomination = int(count.denomination_cents)
            normalized_counts[denomination] = (
                normalized_counts.get(denomination, 0)
                + count.quantity
            )

        total_cents = sum(
            denomination * quantity
            for denomination, quantity
            in normalized_counts.items()
        )

        opening_total = (
            Decimal(total_cents) / Decimal("100")
        ).quantize(Decimal("0.01"))

        shift = PosCashShift(
            branch_id=branch.id,
            terminal_id=terminal_id,
            status="OPEN",
            opened_by_staff_id=requesting_staff.id,
            opening_authorized_by_staff_id=(
                authorizing_manager.id
            ),
            opening_total=opening_total,
        )

        db.add(shift)

        try:
            # shift.id and shift_uuid are needed by counts/audit.
            # The partial unique index is the final race barrier.
            db.flush()
        except IntegrityError as exc:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active cash shift already exists",
            ) from exc

        for denomination, quantity in sorted(
            normalized_counts.items()
        ):
            db.add(
                PosCashDenominationCount(
                    shift_id=shift.id,
                    stage="OPENING",
                    denomination_cents=denomination,
                    quantity=quantity,
                    amount_cents=denomination * quantity,
                )
            )

        PosAuditService.record(
            db,
            event_type="SHIFT_OPENED",
            branch_id=branch.id,
            terminal_id=terminal_id,
            actor_staff_id=requesting_staff.id,
            authorizer_staff_id=authorizing_manager.id,
            target_type="cash_shift",
            target_id=str(shift.shift_uuid),
            metadata={
                "opening_total_cents": total_cents,
                "denominations": [
                    {
                        "denomination_cents": denomination,
                        "quantity": quantity,
                        "amount_cents": denomination * quantity,
                    }
                    for denomination, quantity in sorted(
                        normalized_counts.items()
                    )
                ],
            },
        )

        db.flush()

        return shift
