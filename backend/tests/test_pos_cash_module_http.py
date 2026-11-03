from decimal import Decimal
from uuid import uuid4

from app.api.pos_cash import (
    finalize_cash_shift,
    record_cash_movement,
)
from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_staff import PosStaff, PosStaffRole
from app.schemas.pos_cash import (
    PosCashCloseRequest,
    PosCashMovementRequest,
)
from app.services.pos_cash_service import PosCashService


TERMINAL_ID = "PAPELERIA-HTTP-01"


def _seed_papeleria_staff(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Papeleria HTTP {suffix}",
        code=f"pap-http-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.flush()

    cashier = PosStaff(
        branch_id=branch.id,
        display_name="Papeleria Cashier",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
        module_code="PAPELERIA",
    )

    manager = PosStaff(
        branch_id=branch.id,
        display_name="Papeleria Manager",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2468"),
        is_active=True,
        module_code="PAPELERIA",
    )

    db_session.add_all(
        [
            cashier,
            manager,
        ]
    )

    db_session.commit()

    db_session.refresh(cashier)
    db_session.refresh(manager)

    return branch, cashier, manager


def _papeleria_token(branch):
    return {
        "branch_code": branch.code,
        "terminal_id": TERMINAL_ID,
        "module_code": "PAPELERIA",
    }


def _open_papeleria_shift(
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
        opening_amount=Decimal("1000.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
        module_code="PAPELERIA",
    )

    db_session.commit()
    db_session.refresh(shift)

    return shift


def test_papeleria_cash_movement_route_uses_papeleria_manager(
    db_session,
):
    branch, cashier, manager = (
        _seed_papeleria_staff(db_session)
    )

    shift = _open_papeleria_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    payload = PosCashMovementRequest(
        direction="OUTFLOW",
        category="EXPENSE",
        amount=Decimal("50.00"),
        note="Papeleria test expense",
        idempotency_key=(
            f"pap-http-movement-{uuid4()}"
        ),
        authorizing_manager_staff_id=manager.id,
        manager_pin="2468",
    )

    response = record_cash_movement(
        shift_uuid=shift.shift_uuid,
        payload=payload,
        requesting_staff=cashier,
        token_payload=_papeleria_token(branch),
        db=db_session,
    )

    assert response.shift_id == shift.id
    assert response.amount == Decimal("50.00")
    assert response.authorizing_staff_id == manager.id


def test_papeleria_cash_close_route_uses_papeleria_manager(
    db_session,
):
    branch, cashier, manager = (
        _seed_papeleria_staff(db_session)
    )

    shift = _open_papeleria_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        manager=manager,
    )

    PosCashService.submit_closing_count(
        db_session,
        shift_uuid=shift.shift_uuid,
        staff=cashier,
        closing_amount=Decimal("1000.00"),
    )

    db_session.commit()
    db_session.refresh(shift)

    assert shift.status == "CLOSING"

    payload = PosCashCloseRequest(
        authorizing_manager_staff_id=manager.id,
        manager_pin="2468",
        difference_note=None,
    )

    response = finalize_cash_shift(
        shift_uuid=shift.shift_uuid,
        payload=payload,
        requesting_staff=cashier,
        token_payload=_papeleria_token(branch),
        db=db_session,
    )

    assert response.status == "CLOSED"
