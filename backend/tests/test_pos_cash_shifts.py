from decimal import Decimal
from threading import Barrier, Lock, Thread
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import hash_password
from app.database.session import Base
from app.models.branch import Branch
from app.models.pos_audit import PosAuditEvent
from app.models.pos_staff import PosStaff, PosStaffRole


TERMINAL_ID = "POS-IXTAPA-01"


def _cash_feature():
    try:
        from app.models.pos_cash import (
            PosCashDenominationCount,
            PosCashShift,
        )
        from app.schemas.pos_cash import CashDenominationCount
        from app.services.pos_cash_service import PosCashService
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"POS cash shifts are not implemented yet: {exc}",
            pytrace=False,
        )

    return (
        PosCashShift,
        PosCashDenominationCount,
        CashDenominationCount,
        PosCashService,
    )


def _seed_staff(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Ixtapa Cash {suffix}",
        code=f"ixtapa-cash-{suffix}",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    cashier = PosStaff(
        branch_id=branch.id,
        display_name="Cashier Test",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
    )

    manager = PosStaff(
        branch_id=branch.id,
        display_name="Manager Test",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2468"),
        is_active=True,
    )

    db_session.add_all([cashier, manager])
    db_session.commit()

    db_session.refresh(cashier)
    db_session.refresh(manager)

    return branch, cashier, manager


def _opening_counts(CashDenominationCount):
    return [
        CashDenominationCount(
            denomination_cents=50000,
            quantity=2,
        ),
        CashDenominationCount(
            denomination_cents=20000,
            quantity=1,
        ),
        CashDenominationCount(
            denomination_cents=1000,
            quantity=3,
        ),
    ]


def test_open_shift_calculates_total_from_denominations(
    db_session,
):
    (
        PosCashShift,
        PosCashDenominationCount,
        CashDenominationCount,
        PosCashService,
    ) = _cash_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_counts=_opening_counts(
            CashDenominationCount,
        ),
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    assert isinstance(shift, PosCashShift)
    assert shift.status == "OPEN"
    assert shift.opening_total == Decimal("1230.00")
    assert shift.opened_by_staff_id == cashier.id
    assert shift.opening_authorized_by_staff_id == manager.id

    counts = (
        db_session.query(PosCashDenominationCount)
        .filter(
            PosCashDenominationCount.shift_id == shift.id,
            PosCashDenominationCount.stage == "OPENING",
        )
        .order_by(
            PosCashDenominationCount.denomination_cents.asc()
        )
        .all()
    )

    assert [
        (
            item.denomination_cents,
            item.quantity,
            item.amount_cents,
        )
        for item in counts
    ] == [
        (1000, 3, 3000),
        (20000, 1, 20000),
        (50000, 2, 100000),
    ]


def test_second_open_shift_is_rejected(
    db_session,
):
    (
        _,
        _,
        CashDenominationCount,
        PosCashService,
    ) = _cash_feature()

    branch, cashier, manager = _seed_staff(db_session)

    PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_counts=_opening_counts(
            CashDenominationCount,
        ),
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.open_shift(
            db_session,
            branch_code=branch.code,
            terminal_id=TERMINAL_ID,
            opening_counts=_opening_counts(
                CashDenominationCount,
            ),
            requesting_staff=cashier,
            authorizing_manager=manager,
        )

    assert exc_info.value.status_code == 409


def test_manager_authorization_is_required_to_open_shift(
    db_session,
):
    (
        _,
        _,
        CashDenominationCount,
        PosCashService,
    ) = _cash_feature()

    branch, cashier, _ = _seed_staff(db_session)

    with pytest.raises(HTTPException) as exc_info:
        PosCashService.open_shift(
            db_session,
            branch_code=branch.code,
            terminal_id=TERMINAL_ID,
            opening_counts=_opening_counts(
                CashDenominationCount,
            ),
            requesting_staff=cashier,
            authorizing_manager=cashier,
        )

    assert exc_info.value.status_code == 403


def test_opening_rejects_unknown_denomination():
    (
        _,
        _,
        CashDenominationCount,
        _,
    ) = _cash_feature()

    with pytest.raises(ValidationError):
        CashDenominationCount(
            denomination_cents=300,
            quantity=1,
        )


def test_open_shift_records_shift_opened_audit(
    db_session,
):
    (
        _,
        _,
        CashDenominationCount,
        PosCashService,
    ) = _cash_feature()

    branch, cashier, manager = _seed_staff(db_session)

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=TERMINAL_ID,
        opening_counts=_opening_counts(
            CashDenominationCount,
        ),
        requesting_staff=cashier,
        authorizing_manager=manager,
    )

    db_session.flush()

    event = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type == "SHIFT_OPENED",
            PosAuditEvent.branch_id == branch.id,
            PosAuditEvent.terminal_id == TERMINAL_ID,
        )
        .one()
    )

    assert event.actor_staff_id == cashier.id
    assert event.authorizer_staff_id == manager.id
    assert event.target_type == "cash_shift"
    assert event.target_id == str(shift.shift_uuid)


def test_two_simultaneous_open_attempts_cannot_both_commit(
    tmp_path,
):
    (
        PosCashShift,
        _,
        CashDenominationCount,
        PosCashService,
    ) = _cash_feature()

    db_path = tmp_path / "cash-concurrency.sqlite3"

    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        connect_args={
            "check_same_thread": False,
            "timeout": 10,
        },
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(engine)

    setup_db = SessionLocal()

    try:
        branch, cashier, manager = _seed_staff(setup_db)

        branch_code = branch.code
        branch_id = branch.id
        cashier_id = cashier.id
        manager_id = manager.id
    finally:
        setup_db.close()

    barrier = Barrier(2)
    result_lock = Lock()
    results = []

    def worker():
        db = SessionLocal()

        try:
            cashier = db.get(
                PosStaff,
                cashier_id,
            )
            manager = db.get(
                PosStaff,
                manager_id,
            )

            barrier.wait()

            PosCashService.open_shift(
                db,
                branch_code=branch_code,
                terminal_id=TERMINAL_ID,
                opening_counts=_opening_counts(
                    CashDenominationCount,
                ),
                requesting_staff=cashier,
                authorizing_manager=manager,
            )

            db.commit()
            result = "committed"
        except Exception as exc:
            db.rollback()
            result = type(exc).__name__
        finally:
            db.close()

        with result_lock:
            results.append(result)

    first = Thread(target=worker)
    second = Thread(target=worker)

    first.start()
    second.start()

    first.join(timeout=15)
    second.join(timeout=15)

    assert not first.is_alive()
    assert not second.is_alive()

    assert results.count("committed") == 1
    assert len(results) == 2

    verify_db = SessionLocal()

    try:
        active_count = (
            verify_db.query(PosCashShift)
            .filter(
                PosCashShift.branch_id == branch_id,
                PosCashShift.status.in_(
                    ["OPEN", "CLOSING"]
                ),
            )
            .count()
        )

        assert active_count == 1
    finally:
        verify_db.close()
        engine.dispose()
