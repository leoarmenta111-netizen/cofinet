import pytest

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_staff import PosStaff, PosStaffRole


TERMINAL_ID = "POS-IXTAPA-01"


def _audit_feature():
    try:
        from app.models.pos_audit import PosAuditEvent
        from app.services.pos_audit_service import PosAuditService
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"POS audit log is not implemented yet: {exc}",
            pytrace=False,
        )

    return PosAuditEvent, PosAuditService


def _seed_actor(db_session):
    branch = Branch(
        name="Ixtapa Audit",
        code="ixtapa-audit",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    staff = PosStaff(
        branch_id=branch.id,
        display_name="Audit Manager",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2468"),
        is_active=True,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    return branch, staff


def test_audit_event_records_actor_and_target(
    db_session,
):
    PosAuditEvent, PosAuditService = _audit_feature()
    branch, staff = _seed_actor(db_session)

    event = PosAuditService.record(
        db_session,
        event_type="SHIFT_OPENED",
        branch_id=branch.id,
        terminal_id=TERMINAL_ID,
        actor_staff_id=staff.id,
        target_type="cash_shift",
        target_id="shift-test-001",
    )

    db_session.commit()
    db_session.expire_all()

    stored = db_session.get(
        PosAuditEvent,
        event.id,
    )

    assert stored is not None
    assert stored.event_type == "SHIFT_OPENED"
    assert stored.branch_id == branch.id
    assert stored.terminal_id == TERMINAL_ID
    assert stored.actor_staff_id == staff.id
    assert stored.authorizer_staff_id is None
    assert stored.target_type == "cash_shift"
    assert stored.target_id == "shift-test-001"


def test_audit_metadata_round_trips(
    db_session,
):
    PosAuditEvent, PosAuditService = _audit_feature()
    branch, staff = _seed_actor(db_session)

    metadata = {
        "opening_amount_cents": 150000,
        "source": "manager_open",
        "denominations": {
            "500": 2,
            "200": 1,
        },
    }

    event = PosAuditService.record(
        db_session,
        event_type="SHIFT_OPENED",
        branch_id=branch.id,
        terminal_id=TERMINAL_ID,
        actor_staff_id=staff.id,
        authorizer_staff_id=staff.id,
        target_type="cash_shift",
        target_id="shift-test-002",
        metadata=metadata,
    )

    db_session.commit()
    db_session.expire_all()

    stored = db_session.get(
        PosAuditEvent,
        event.id,
    )

    assert stored is not None
    assert stored.authorizer_staff_id == staff.id
    assert stored.metadata_json == metadata
