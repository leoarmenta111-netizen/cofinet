from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_cash import (
    ACTIVE_SHIFT_STATUSES,
    PosCashDenominationCount,
    PosCashLedgerEntry,
    PosCashMovement,
    PosCashShift,
)
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.schemas.pos_cash import (
    CashDenominationCount,
    PosCashReconciliation,
)
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
        opening_counts: list[CashDenominationCount] | None = None,
        opening_amount: Decimal | None = None,
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

        has_amount = opening_amount is not None
        has_counts = bool(opening_counts)

        if has_amount == has_counts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Provide exactly one opening amount "
                    "or denomination count"
                ),
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

        if opening_amount is not None:
            opening_total = Decimal(
                str(opening_amount)
            ).quantize(
                Decimal("0.01")
            )

            if opening_total < 0:
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_ENTITY
                    ),
                    detail=(
                        "Opening amount cannot be negative"
                    ),
                )

            total_cents = int(
                opening_total * Decimal("100")
            )

        else:
            for count in opening_counts or []:
                denomination = int(
                    count.denomination_cents
                )
                normalized_counts[denomination] = (
                    normalized_counts.get(
                        denomination,
                        0,
                    )
                    + count.quantity
                )

            total_cents = sum(
                denomination * quantity
                for denomination, quantity
                in normalized_counts.items()
            )

            opening_total = (
                Decimal(total_cents)
                / Decimal("100")
            ).quantize(
                Decimal("0.01")
            )

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

    @staticmethod
    def append_ledger_entry(
        db: Session,
        *,
        shift_id: int,
        entry_type: str,
        amount: Decimal,
        idempotency_key: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> PosCashLedgerEntry:
        key = idempotency_key.strip()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency key is required",
            )

        existing = db.execute(
            select(PosCashLedgerEntry).where(
                PosCashLedgerEntry.idempotency_key == key
            )
        ).scalar_one_or_none()

        if existing is not None:
            return existing

        normalized_amount = Decimal(str(amount)).quantize(
            Decimal("0.01")
        )

        if (
            not normalized_amount.is_finite()
            or normalized_amount == Decimal("0.00")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ledger amount must be non-zero",
            )

        entry = PosCashLedgerEntry(
            shift_id=shift_id,
            entry_type=entry_type,
            amount=normalized_amount,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
        )

        db.add(entry)
        db.flush()

        return entry

    @classmethod
    def record_movement(
        cls,
        db: Session,
        *,
        shift_uuid: str,
        direction: str,
        category: str,
        amount: Decimal,
        note: str,
        idempotency_key: str,
        requesting_staff: PosStaff,
        authorizing_manager: PosStaff,
    ) -> PosCashMovement:
        valid_directions = {
            "INFLOW",
            "OUTFLOW",
        }

        valid_categories = {
            "CHANGE",
            "EXPENSE",
            "SAFE_WITHDRAWAL",
            "DEPOSIT",
            "CORRECTION",
            "OTHER",
        }

        if direction not in valid_directions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid cash movement direction",
            )

        if category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid cash movement category",
            )

        normalized_note = note.strip()

        if not normalized_note:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cash movement note is required",
            )

        key = idempotency_key.strip()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency key is required",
            )

        normalized_amount = Decimal(str(amount)).quantize(
            Decimal("0.01")
        )

        if (
            not normalized_amount.is_finite()
            or normalized_amount <= Decimal("0.00")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cash movement amount must be positive",
            )

        shift = db.execute(
            select(PosCashShift)
            .where(
                PosCashShift.shift_uuid == shift_uuid
            )
            .with_for_update()
        ).scalar_one_or_none()

        if shift is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash shift not found",
            )

        cls._validate_staff(
            staff=requesting_staff,
            branch_id=shift.branch_id,
        )

        cls._validate_staff(
            staff=authorizing_manager,
            branch_id=shift.branch_id,
        )

        if (
            cls._staff_role(authorizing_manager)
            != PosStaffRole.MANAGER.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager authorization required",
            )

        existing = db.execute(
            select(PosCashMovement).where(
                PosCashMovement.idempotency_key == key
            )
        ).scalar_one_or_none()

        if existing is not None:
            same_request = (
                existing.shift_id == shift.id
                and existing.direction == direction
                and existing.category == category
                and existing.amount == normalized_amount
                and existing.note == normalized_note
                and existing.requesting_staff_id
                == requesting_staff.id
                and existing.authorizing_staff_id
                == authorizing_manager.id
            )

            if not same_request:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Idempotency key was already used "
                        "for a different cash movement"
                    ),
                )

            return existing

        if shift.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cash shift is not open",
            )

        movement = PosCashMovement(
            shift_id=shift.id,
            direction=direction,
            category=category,
            amount=normalized_amount,
            note=normalized_note,
            requesting_staff_id=requesting_staff.id,
            authorizing_staff_id=authorizing_manager.id,
            idempotency_key=key,
        )

        db.add(movement)
        db.flush()

        signed_amount = (
            normalized_amount
            if direction == "INFLOW"
            else -normalized_amount
        )

        cls.append_ledger_entry(
            db,
            shift_id=shift.id,
            entry_type=(
                "MANUAL_INFLOW"
                if direction == "INFLOW"
                else "MANUAL_OUTFLOW"
            ),
            amount=signed_amount,
            idempotency_key=key,
            reference_type="cash_movement",
            reference_id=str(movement.movement_uuid),
        )

        PosAuditService.record(
            db,
            event_type="CASH_MOVEMENT",
            branch_id=shift.branch_id,
            terminal_id=shift.terminal_id,
            actor_staff_id=requesting_staff.id,
            authorizer_staff_id=authorizing_manager.id,
            target_type="cash_movement",
            target_id=str(movement.movement_uuid),
            metadata={
                "shift_uuid": shift.shift_uuid,
                "direction": direction,
                "category": category,
                "amount": str(normalized_amount),
                "note": normalized_note,
                "idempotency_key": key,
            },
        )

        db.flush()

        return movement

    @classmethod
    def submit_closing_count(
        cls,
        db: Session,
        *,
        shift_uuid: str,
        closing_counts: list[CashDenominationCount],
        staff: PosStaff,
    ) -> PosCashReconciliation:
        if not closing_counts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Closing denomination count is required",
            )

        shift = db.execute(
            select(PosCashShift)
            .where(
                PosCashShift.shift_uuid == shift_uuid
            )
            .with_for_update()
        ).scalar_one_or_none()

        if shift is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash shift not found",
            )

        cls._validate_staff(
            staff=staff,
            branch_id=shift.branch_id,
        )

        if shift.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cash shift is not open",
            )

        normalized_counts: dict[int, int] = {}

        for count in closing_counts:
            denomination = int(count.denomination_cents)

            normalized_counts[denomination] = (
                normalized_counts.get(denomination, 0)
                + count.quantity
            )

        counted_cents = sum(
            denomination * quantity
            for denomination, quantity
            in normalized_counts.items()
        )

        counted_cash = (
            Decimal(counted_cents) / Decimal("100")
        ).quantize(Decimal("0.01"))

        ledger_total_raw = db.execute(
            select(
                func.coalesce(
                    func.sum(PosCashLedgerEntry.amount),
                    0,
                )
            ).where(
                PosCashLedgerEntry.shift_id == shift.id
            )
        ).scalar_one()

        ledger_total = Decimal(
            str(ledger_total_raw)
        ).quantize(Decimal("0.01"))

        expected_cash = (
            Decimal(str(shift.opening_total))
            + ledger_total
        ).quantize(Decimal("0.01"))

        difference = (
            counted_cash - expected_cash
        ).quantize(Decimal("0.01"))

        for denomination, quantity in sorted(
            normalized_counts.items()
        ):
            db.add(
                PosCashDenominationCount(
                    shift_id=shift.id,
                    stage="CLOSING",
                    denomination_cents=denomination,
                    quantity=quantity,
                    amount_cents=denomination * quantity,
                )
            )

        shift.status = "CLOSING"
        shift.closed_by_staff_id = staff.id
        shift.closing_total = counted_cash
        shift.expected_total = expected_cash
        shift.variance = difference
        shift.variance_note = None

        db.flush()

        return PosCashReconciliation(
            shift_uuid=shift.shift_uuid,
            status="CLOSING",
            counted_cash=counted_cash,
            expected_cash=expected_cash,
            difference=difference,
        )

    @classmethod
    def authorize_close(
        cls,
        db: Session,
        *,
        shift_uuid: str,
        manager: PosStaff,
        difference_note: str | None = None,
    ) -> PosCashShift:
        shift = db.execute(
            select(PosCashShift)
            .where(
                PosCashShift.shift_uuid == shift_uuid
            )
            .with_for_update()
        ).scalar_one_or_none()

        if shift is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash shift not found",
            )

        cls._validate_staff(
            staff=manager,
            branch_id=shift.branch_id,
        )

        if (
            cls._staff_role(manager)
            != PosStaffRole.MANAGER.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager authorization required",
            )

        if shift.status != "CLOSING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cash shift is not awaiting final close",
            )

        if (
            shift.closing_total is None
            or shift.expected_total is None
            or shift.variance is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cash reconciliation is incomplete",
            )

        difference = Decimal(
            str(shift.variance)
        ).quantize(Decimal("0.01"))

        normalized_note = (
            difference_note.strip()
            if difference_note is not None
            else ""
        )

        if (
            difference != Decimal("0.00")
            and not normalized_note
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Difference note is required "
                    "when counted cash differs from expected cash"
                ),
            )

        shift.status = "CLOSED"
        shift.closing_authorized_by_staff_id = manager.id
        shift.variance_note = normalized_note or None
        shift.closed_at = datetime.now(timezone.utc)

        PosAuditService.record(
            db,
            event_type="SHIFT_CLOSED",
            branch_id=shift.branch_id,
            terminal_id=shift.terminal_id,
            actor_staff_id=shift.closed_by_staff_id,
            authorizer_staff_id=manager.id,
            target_type="cash_shift",
            target_id=str(shift.shift_uuid),
            metadata={
                "counted_cash": str(shift.closing_total),
                "expected_cash": str(shift.expected_total),
                "difference": str(shift.variance),
                "difference_note": shift.variance_note,
            },
        )

        db.flush()

        return shift
