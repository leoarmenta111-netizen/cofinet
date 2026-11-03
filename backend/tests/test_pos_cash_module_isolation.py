from decimal import Decimal
from uuid import uuid4

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_audit import PosAuditEvent
from app.models.pos_cash import PosCashShift
from app.models.pos_staff import PosStaff, PosStaffRole
from app.services.pos_cash_service import PosCashService


TERMINAL_ID = "POS-SHARED-TERMINAL-01"


def _require_module_fields():
    assert hasattr(
        PosStaff,
        "module_code",
    ), (
        "RED expected: PosStaff.module_code "
        "has not been implemented yet"
    )

    assert hasattr(
        PosCashShift,
        "module_code",
    ), (
        "RED expected: PosCashShift.module_code "
        "has not been implemented yet"
    )

    assert hasattr(
        PosAuditEvent,
        "module_code",
    ), (
        "RED expected: PosAuditEvent.module_code "
        "has not been implemented yet"
    )


def _seed_context(db_session):
    _require_module_fields()

    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Cash Module {suffix}",
        code=f"cash-module-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.flush()

    cafe_cashier = PosStaff(
        branch_id=branch.id,
        display_name="Cafe Cashier",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
        module_code="CAFE",
    )

    cafe_manager = PosStaff(
        branch_id=branch.id,
        display_name="Cafe Manager",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2222"),
        is_active=True,
        module_code="CAFE",
    )

    papeleria_cashier = PosStaff(
        branch_id=branch.id,
        display_name="Papeleria Cashier",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("3333"),
        is_active=True,
        module_code="PAPELERIA",
    )

    papeleria_manager = PosStaff(
        branch_id=branch.id,
        display_name="Papeleria Manager",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("4444"),
        is_active=True,
        module_code="PAPELERIA",
    )

    db_session.add_all(
        [
            cafe_cashier,
            cafe_manager,
            papeleria_cashier,
            papeleria_manager,
        ]
    )

    db_session.commit()

    return (
        branch,
        cafe_cashier,
        cafe_manager,
        papeleria_cashier,
        papeleria_manager,
    )


def test_cafe_and_papeleria_can_have_separate_active_shift_on_same_terminal_id(
    db_session,
):
    (
        branch,
        cafe_cashier,
        cafe_manager,
        papeleria_cashier,
        papeleria_manager,
    ) = _seed_context(db_session)

    cafe_shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_amount=Decimal("500.00"),
        requesting_staff=cafe_cashier,
        authorizing_manager=cafe_manager,
        module_code="CAFE",
    )

    db_session.commit()

    papeleria_shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_amount=Decimal("800.00"),
        requesting_staff=papeleria_cashier,
        authorizing_manager=papeleria_manager,
        module_code="PAPELERIA",
    )

    db_session.commit()

    assert cafe_shift.id != papeleria_shift.id
    assert cafe_shift.module_code == "CAFE"
    assert (
        papeleria_shift.module_code
        == "PAPELERIA"
    )


def test_cash_shift_lookup_is_scoped_by_module(
    db_session,
):
    (
        branch,
        cafe_cashier,
        cafe_manager,
        papeleria_cashier,
        papeleria_manager,
    ) = _seed_context(db_session)

    cafe_shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_amount=Decimal("500.00"),
        requesting_staff=cafe_cashier,
        authorizing_manager=cafe_manager,
        module_code="CAFE",
    )

    db_session.commit()

    papeleria_shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_amount=Decimal("800.00"),
        requesting_staff=papeleria_cashier,
        authorizing_manager=papeleria_manager,
        module_code="PAPELERIA",
    )

    db_session.commit()

    found_cafe = PosCashService.current_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        module_code="CAFE",
    )

    found_papeleria = PosCashService.current_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        module_code="PAPELERIA",
    )

    assert found_cafe.id == cafe_shift.id
    assert (
        found_papeleria.id
        == papeleria_shift.id
    )


def test_audit_event_records_module_code(
    db_session,
):
    (
        branch,
        _,
        _,
        papeleria_cashier,
        papeleria_manager,
    ) = _seed_context(db_session)

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_amount=Decimal("800.00"),
        requesting_staff=papeleria_cashier,
        authorizing_manager=papeleria_manager,
        module_code="PAPELERIA",
    )

    db_session.flush()

    event = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type
            == "SHIFT_OPENED",
            PosAuditEvent.target_id
            == str(shift.shift_uuid),
        )
        .one()
    )

    assert (
        event.module_code
        == "PAPELERIA"
    )
