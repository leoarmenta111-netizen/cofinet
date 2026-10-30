import pytest
from fastapi import HTTPException

from app.auth.security import hash_password
from app.models.branch import Branch


PIN = "2468"
TERMINAL_ID = "POS-IXTAPA-01"


def _staff_feature():
    """
    Delay imports so the RED state is an assertion failure caused by the
    missing feature rather than a pytest collection/import error.
    """
    try:
        from app.models.pos_staff import PosStaff, PosStaffRole
        from app.services.pos_staff_service import PosStaffService
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"POS staff authentication is not implemented yet: {exc}",
            pytrace=False,
        )

    return PosStaff, PosStaffRole, PosStaffService


def _seed_branch(db_session):
    branch = Branch(
        name="Ixtapa",
        code="ixtapa",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()
    return branch


def _seed_staff(
    db_session,
    *,
    role_name="CASHIER",
    is_active=True,
):
    PosStaff, PosStaffRole, _ = _staff_feature()
    branch = _seed_branch(db_session)

    staff = PosStaff(
        branch_id=branch.id,
        display_name="Test Staff",
        role=getattr(PosStaffRole, role_name),
        pin_hash=hash_password(PIN),
        is_active=is_active,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    return branch, staff


def _unlock_payload(staff_id, pin=PIN):
    return {
        "staff_id": staff_id,
        "pin": pin,
        "branch_code": "ixtapa",
        "terminal_id": TERMINAL_ID,
    }


def test_cashier_can_unlock_with_correct_pin(
    client,
    db_session,
):
    branch, staff = _seed_staff(db_session)

    response = client.post(
        "/pos/staff/unlock",
        json=_unlock_payload(staff.id),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["staff_id"] == staff.id
    assert body["display_name"] == staff.display_name
    assert body["role"] == "CASHIER"
    assert body["branch_code"] == branch.code
    assert body["terminal_id"] == TERMINAL_ID
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_wrong_pin_is_rejected(
    client,
    db_session,
):
    _, staff = _seed_staff(db_session)

    response = client.post(
        "/pos/staff/unlock",
        json=_unlock_payload(
            staff.id,
            pin="9999",
        ),
    )

    assert response.status_code == 401


def test_inactive_staff_is_rejected(
    client,
    db_session,
):
    _, staff = _seed_staff(
        db_session,
        is_active=False,
    )

    response = client.post(
        "/pos/staff/unlock",
        json=_unlock_payload(staff.id),
    )

    assert response.status_code == 403


def test_cashier_cannot_authorize_manager_operation(
    db_session,
):
    _, staff = _seed_staff(db_session)
    _, _, PosStaffService = _staff_feature()

    with pytest.raises(HTTPException) as exc_info:
        PosStaffService.authorize_manager(
            db_session,
            staff_id=staff.id,
            pin=PIN,
            branch_code="ixtapa",
        )

    assert exc_info.value.status_code == 403


def test_staff_session_returns_authenticated_employee(
    client,
    db_session,
):
    branch, staff = _seed_staff(db_session)

    unlock = client.post(
        "/pos/staff/unlock",
        json=_unlock_payload(staff.id),
    )

    assert unlock.status_code == 200

    token = unlock.json()["access_token"]

    response = client.get(
        "/pos/staff/session",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["staff_id"] == staff.id
    assert body["display_name"] == staff.display_name
    assert body["role"] == "CASHIER"
    assert body["branch_code"] == branch.code
    assert body["terminal_id"] == TERMINAL_ID
