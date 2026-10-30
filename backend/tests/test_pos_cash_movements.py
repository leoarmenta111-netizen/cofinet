from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_audit import PosAuditEvent
from app.models.pos_cash import PosCashShift
from app.models.pos_staff import PosStaff, PosStaffRole
from app.schemas.pos_cash import CashDenominationCount
from app.services.pos_cash_service import PosCashService


TERMINAL_ID = "POS-IXTAPA-01"


def _movement_feature():
    try:
        from app.models.pos_cash import (
            PosCashLedgerEntry,
            PosCashMovement,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(
            f"POS cash movement ledger is not implemented yet: {exc}",
            pytrace=False,
        )

    return PosCashMovement, PosCashLedgerEntry


def _seed_staff(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Ixtapa Movement {suffix}",
        code=f"ixtapa-movement-{suffix}",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    cashier = PosStaff(
        branch_id=branch.id,
        display_name="Cashier Movement",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
    )

    manager = PosStaff(
        branch_id=branch.id,
        display_name="Manager Movement",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2468"),
        is_active=True,
    )

    db_session.add_all([cashier, manager])
    db_session.commit()

    db_session.refresh(cashier)
    db_session.refresh(manager)

    return branch, cashier, manager


def _open_shift(
    db_session,
    *,
    branch,
    cashier,
    manager,
):
    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_counts=[
            CashDenominationCount(
                denomination_cents=50000,
                quantity=2,
            ),
        ],
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.commit()
    db_session.refresh(shift)

    return shift


def _ledger_total(
    db_session,
    PosCashLedgerEntry,
    shift_id,
):
    value = (
        db_session.query(
            func.coalesce(
                func.sum(PosCashLedgerEntry.amount),
                0,
            )
        )
        .filter(
            PosCashLedgerEntry.shift_id == shift_id,
        )
        .scalar()
    )

    return Decimal(str(value))


def test_manager_authorized_inflow_increases_expected_cash(
    db_session,
):
    PosCashMovement, PosCashLedgerEntry = _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    movement = PosCashService.record_movement(
        db_session,
        shift_uuid=shift.shift_uuid,
        direction="INFLOW",
        category="DEPOSIT",
        amount=Decimal("250.00"),
        note="Additional change fund",
        idempotency_key=f"movement-{uuid4()}",
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    assert isinstance(movement, PosCashMovement)
    assert movement.amount == Decimal("250.00")
    assert movement.direction == "INFLOW"

    ledger_total = _ledger_total(
        db_session,
        PosCashLedgerEntry,
        shift.id,
    )

    assert ledger_total == Decimal("250.00")
    assert (
        shift.opening_total + ledger_total
        == Decimal("1250.00")
    )

    audit = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type == "CASH_MOVEMENT",
            PosAuditEvent.target_type == "cash_movement",
            PosAuditEvent.target_id == str(
                movement.movement_uuid
            ),
        )
        .one()
    )

    assert audit.actor_staff_id == cashier.id
    assert audit.authorizer_staff_id == manager.id


def test_manager_authorized_outflow_reduces_expected_cash(
    db_session,
):
    _, PosCashLedgerEntry = _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.record_movement(
        db_session,
        shift_uuid=shift.shift_uuid,
        direction="OUTFLOW",
        category="EXPENSE",
        amount=Decimal("175.50"),
        note="Petty cash expense",
        idempotency_key=f"movement-{uuid4()}",
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    ledger_total = _ledger_total(
        db_session,
        PosCashLedgerEntry,
        shift.id,
    )

    assert ledger_total == Decimal("-175.50")
    assert (
        shift.opening_total + ledger_total
        == Decimal("824.50")
    )


def test_cash_movement_requires_note(
    db_session,
):
    _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.record_movement(
            db_session,
            shift_uuid=shift.shift_uuid,
            direction="INFLOW",
            category="CHANGE",
            amount=Decimal("100.00"),
            note="   ",
            idempotency_key=f"movement-{uuid4()}",
            requesting_staff=cashier,
            authorizing_manager=manager,
        )

    assert exc_info.value.status_code == 422


def test_cashier_cannot_authorize_cash_movement(
    db_session,
):
    _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.record_movement(
            db_session,
            shift_uuid=shift.shift_uuid,
            direction="INFLOW",
            category="DEPOSIT",
            amount=Decimal("100.00"),
            note="Unauthorized attempt",
            idempotency_key=f"movement-{uuid4()}",
            requesting_staff=cashier,
            authorizing_manager=cashier,
        )

    assert exc_info.value.status_code == 403


def test_movement_is_rejected_when_shift_is_not_open(
    db_session,
):
    _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    shift.status = "CLOSED"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.record_movement(
            db_session,
            shift_uuid=shift.shift_uuid,
            direction="OUTFLOW",
            category="SAFE_WITHDRAWAL",
            amount=Decimal("500.00"),
            note="Safe withdrawal",
            idempotency_key=f"movement-{uuid4()}",
            requesting_staff=cashier,
            authorizing_manager=manager,
        )

    assert exc_info.value.status_code == 409


def test_repeated_idempotency_key_does_not_duplicate_movement(
    db_session,
):
    PosCashMovement, PosCashLedgerEntry = _movement_feature()

    branch, cashier, manager = _seed_staff(db_session)
    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    key = f"movement-{uuid4()}"

    first = PosCashService.record_movement(
        db_session,
        shift_uuid=shift.shift_uuid,
        direction="INFLOW",
        category="CORRECTION",
        amount=Decimal("50.00"),
        note="Drawer correction",
        idempotency_key=key,
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    second = PosCashService.record_movement(
        db_session,
        shift_uuid=shift.shift_uuid,
        direction="INFLOW",
        category="CORRECTION",
        amount=Decimal("50.00"),
        note="Drawer correction",
        idempotency_key=key,
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    assert second.id == first.id

    movement_count = (
        db_session.query(PosCashMovement)
        .filter(
            PosCashMovement.idempotency_key == key,
        )
        .count()
    )

    ledger_count = (
        db_session.query(PosCashLedgerEntry)
        .filter(
            PosCashLedgerEntry.idempotency_key == key,
        )
        .count()
    )

    audit_count = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type == "CASH_MOVEMENT",
            PosAuditEvent.target_type == "cash_movement",
            PosAuditEvent.target_id == str(
                first.movement_uuid
            ),
        )
        .count()
    )

    assert movement_count == 1
    assert ledger_count == 1
    assert audit_count == 1
