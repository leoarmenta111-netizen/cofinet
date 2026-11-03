from uuid import uuid4

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_staff import PosStaff, PosStaffRole


PIN = "2468"
TERMINAL_ID = "POS-MODULE-TEST-01"


def _seed_branch(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Module Test {suffix}",
        code=f"module-test-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.flush()

    return branch


def _seed_staff(
    db_session,
    *,
    branch,
    module_code,
    role=PosStaffRole.CASHIER,
):
    assert hasattr(
        PosStaff,
        "module_code",
    ), (
        "RED expected: PosStaff.module_code "
        "has not been implemented yet"
    )

    staff = PosStaff(
        branch_id=branch.id,
        display_name=f"{module_code} Staff",
        role=role,
        pin_hash=hash_password(PIN),
        is_active=True,
        module_code=module_code,
    )

    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    return staff


def _unlock(
    client,
    *,
    staff,
    branch,
    module_code=None,
):
    payload = {
        "staff_id": staff.id,
        "pin": PIN,
        "branch_code": branch.code,
        "terminal_id": TERMINAL_ID,
    }

    if module_code is not None:
        payload["module_code"] = module_code

    return client.post(
        "/pos/staff/unlock",
        json=payload,
    )


def test_cafe_staff_token_defaults_to_cafe_module(
    client,
    db_session,
):
    branch = _seed_branch(db_session)

    staff = _seed_staff(
        db_session,
        branch=branch,
        module_code="CAFE",
    )

    response = _unlock(
        client,
        staff=staff,
        branch=branch,
    )

    assert response.status_code == 200

    body = response.json()

    assert body.get("module_code") == "CAFE"

    session = client.get(
        "/pos/staff/session",
        headers={
            "Authorization":
                f"Bearer {body['access_token']}",
        },
    )

    assert session.status_code == 200
    assert session.json().get(
        "module_code"
    ) == "CAFE"


def test_papeleria_staff_token_contains_papeleria_module(
    client,
    db_session,
):
    branch = _seed_branch(db_session)

    staff = _seed_staff(
        db_session,
        branch=branch,
        module_code="PAPELERIA",
    )

    response = _unlock(
        client,
        staff=staff,
        branch=branch,
        module_code="PAPELERIA",
    )

    assert response.status_code == 200

    body = response.json()

    assert body.get(
        "module_code"
    ) == "PAPELERIA"

    session = client.get(
        "/pos/staff/session",
        headers={
            "Authorization":
                f"Bearer {body['access_token']}",
        },
    )

    assert session.status_code == 200
    assert session.json().get(
        "module_code"
    ) == "PAPELERIA"


def test_papeleria_staff_cannot_unlock_cafe_session(
    client,
    db_session,
):
    branch = _seed_branch(db_session)

    staff = _seed_staff(
        db_session,
        branch=branch,
        module_code="PAPELERIA",
    )

    response = _unlock(
        client,
        staff=staff,
        branch=branch,
        module_code="CAFE",
    )

    assert response.status_code == 403


def test_cafe_staff_cannot_unlock_papeleria_session(
    client,
    db_session,
):
    branch = _seed_branch(db_session)

    staff = _seed_staff(
        db_session,
        branch=branch,
        module_code="CAFE",
    )

    response = _unlock(
        client,
        staff=staff,
        branch=branch,
        module_code="PAPELERIA",
    )

    assert response.status_code == 403
