from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_audit import PosAuditEvent
from app.models.pos_staff import PosStaff, PosStaffRole
from app.schemas.pos_cash import (
    CashDenominationCount,
    PosCashShiftResponse,
)
from app.services.pos_cash_service import PosCashService


TERMINAL_ID = "POS-IXTAPA-01"


def _close_feature():
    try:
        from app.schemas.pos_cash import PosCashReconciliation
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(
            f"POS blind closing is not implemented yet: {exc}",
            pytrace=False,
        )

    if not hasattr(
        PosCashService,
        "submit_closing_count",
    ):
        pytest.fail(
            "POS blind closing is not implemented yet: "
            "PosCashService.submit_closing_count is missing",
            pytrace=False,
        )

    if not hasattr(
        PosCashService,
        "authorize_close",
    ):
        pytest.fail(
            "POS blind closing is not implemented yet: "
            "PosCashService.authorize_close is missing",
            pytrace=False,
        )

    return PosCashReconciliation


def _seed_staff(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Ixtapa Close {suffix}",
        code=f"ixtapa-close-{suffix}",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    cashier = PosStaff(
        branch_id=branch.id,
        display_name="Closing Cashier",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
    )

    manager = PosStaff(
        branch_id=branch.id,
        display_name="Closing Manager",
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


def _record_outflow(
    db_session,
    *,
    shift,
    cashier,
    manager,
    amount=Decimal("200.00"),
):
    movement = PosCashService.record_movement(
        db_session,
        shift_uuid=shift.shift_uuid,
        direction="OUTFLOW",
        category="EXPENSE",
        amount=amount,
        note="Closing test expense",
        idempotency_key=f"close-outflow-{uuid4()}",
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.commit()

    return movement


def _matching_800_counts():
    return [
        CashDenominationCount(
            denomination_cents=50000,
            quantity=1,
        ),
        CashDenominationCount(
            denomination_cents=20000,
            quantity=1,
        ),
        CashDenominationCount(
            denomination_cents=10000,
            quantity=1,
        ),
    ]


def _mismatch_700_counts():
    return [
        CashDenominationCount(
            denomination_cents=50000,
            quantity=1,
        ),
        CashDenominationCount(
            denomination_cents=20000,
            quantity=1,
        ),
    ]


def test_open_shift_response_does_not_expose_expected_cash(
    db_session,
):
    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    payload = (
        PosCashShiftResponse
        .model_validate(shift)
        .model_dump()
    )

    assert "expected_cash" not in payload
    assert "expected_total" not in payload
    assert "difference" not in payload
    assert "variance" not in payload


def test_closing_count_calculates_total_from_denominations(
    db_session,
):
    PosCashReconciliation = _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    reconciliation = PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=_matching_800_counts(),
        staff=cashier,
    )

    db_session.flush()

    assert isinstance(
        reconciliation,
        PosCashReconciliation,
    )
    assert reconciliation.counted_cash == Decimal("800.00")


def test_closing_count_reveals_reconciliation_only_after_submission(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    _record_outflow(
        db_session,
        shift=shift,
        cashier=cashier,
        manager=manager,
    )

    before = (
        PosCashShiftResponse
        .model_validate(shift)
        .model_dump()
    )

    assert "expected_total" not in before
    assert "variance" not in before

    reconciliation = PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=_mismatch_700_counts(),
        staff=cashier,
    )

    assert reconciliation.expected_cash == Decimal("800.00")
    assert reconciliation.counted_cash == Decimal("700.00")
    assert reconciliation.difference == Decimal("-100.00")


def test_closing_count_transitions_shift_to_closing(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=_matching_800_counts(),
        staff=cashier,
    )

    db_session.flush()
    db_session.refresh(shift)

    assert shift.status == "CLOSING"
    assert shift.closing_total == Decimal("800.00")


def test_difference_requires_note_before_final_close(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    _record_outflow(
        db_session,
        shift=shift,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=_mismatch_700_counts(),
        staff=cashier,
    )

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.authorize_close(
            db_session,
            shift_uuid=shift.shift_uuid,
            manager=manager,
            difference_note=None,
        )

    assert exc_info.value.status_code == 422


def test_matching_count_does_not_require_difference_note(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    _record_outflow(
        db_session,
        shift=shift,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=_matching_800_counts(),
        staff=cashier,
    )

    closed = PosCashService.authorize_close(
        db_session,
        shift_uuid=shift.shift_uuid,
        manager=manager,
        difference_note=None,
    )

    assert closed.status == "CLOSED"


def test_cashier_cannot_finalize_close(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=[
            CashDenominationCount(
                denomination_cents=50000,
                quantity=2,
            ),
        ],
        staff=cashier,
    )

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.authorize_close(
            db_session,
            shift_uuid=shift.shift_uuid,
            manager=cashier,
            difference_note=None,
        )

    assert exc_info.value.status_code == 403


def test_manager_can_finalize_close(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=[
            CashDenominationCount(
                denomination_cents=50000,
                quantity=2,
            ),
        ],
        staff=cashier,
    )

    closed = PosCashService.authorize_close(
        db_session,
        shift_uuid=shift.shift_uuid,
        manager=manager,
        difference_note=None,
    )

    db_session.flush()

    assert closed.status == "CLOSED"
    assert closed.closed_at is not None
    assert closed.closing_authorized_by_staff_id == manager.id

    audit = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type == "SHIFT_CLOSED",
            PosAuditEvent.target_type == "cash_shift",
            PosAuditEvent.target_id == str(
                shift.shift_uuid
            ),
        )
        .one()
    )

    assert audit.authorizer_staff_id == manager.id


def test_closed_shift_rejects_additional_cash_movements(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=[
            CashDenominationCount(
                denomination_cents=50000,
                quantity=2,
            ),
        ],
        staff=cashier,
    )

    PosCashService.authorize_close(
        db_session,
        shift_uuid=shift.shift_uuid,
        manager=manager,
        difference_note=None,
    )

    db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.record_movement(
            db_session,
            shift_uuid=shift.shift_uuid,
            direction="INFLOW",
            category="DEPOSIT",
            amount=Decimal("50.00"),
            note="Must not be accepted",
            idempotency_key=f"closed-{uuid4()}",
            requesting_staff=cashier,
            authorizing_manager=manager,
        )

    assert exc_info.value.status_code == 409


def test_closed_shift_cannot_be_closed_twice(
    db_session,
):
    _close_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        closing_counts=[
            CashDenominationCount(
                denomination_cents=50000,
                quantity=2,
            ),
        ],
        staff=cashier,
    )

    PosCashService.authorize_close(
        db_session,
        shift_uuid=shift.shift_uuid,
        manager=manager,
        difference_note=None,
    )

    db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.authorize_close(
            db_session,
            shift_uuid=shift.shift_uuid,
            manager=manager,
            difference_note=None,
        )

    assert exc_info.value.status_code == 409
