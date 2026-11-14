from uuid import uuid4

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_staff import PosStaff, PosStaffRole
from app.models.pos_staff_module import PosStaffModule


PIN = "2468"
TERMINAL_ID = "MULTIMODULE-POS-01"


def test_same_staff_can_unlock_cafe_and_papeleria(
    client,
    db_session,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Multi Module {suffix}",
        code=f"multi-module-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.flush()

    staff = PosStaff(
        branch_id=branch.id,
        display_name="Multi Module Staff",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password(PIN),
        is_active=True,
        module_code="CAFE",
    )

    db_session.add(staff)
    db_session.flush()

    db_session.add_all(
        [
            PosStaffModule(
                staff_id=staff.id,
                module_code="CAFE",
            ),
            PosStaffModule(
                staff_id=staff.id,
                module_code="PAPELERIA",
            ),
        ]
    )

    db_session.commit()
    db_session.refresh(staff)

    cafe = client.post(
        "/pos/staff/unlock",
        json={
            "staff_id": staff.id,
            "pin": PIN,
            "branch_code": branch.code,
            "terminal_id": TERMINAL_ID,
            "module_code": "CAFE",
        },
    )

    assert cafe.status_code == 200
    assert cafe.json()["staff_id"] == staff.id
    assert cafe.json()["module_code"] == "CAFE"

    cafe_session = client.get(
        "/pos/staff/session",
        headers={
            "Authorization":
                f"Bearer {cafe.json()['access_token']}",
        },
    )

    assert cafe_session.status_code == 200
    assert (
        cafe_session.json()["module_code"]
        == "CAFE"
    )

    papeleria = client.post(
        "/pos/staff/unlock",
        json={
            "staff_id": staff.id,
            "pin": PIN,
            "branch_code": branch.code,
            "terminal_id": TERMINAL_ID,
            "module_code": "PAPELERIA",
        },
    )

    assert papeleria.status_code == 200
    assert papeleria.json()["staff_id"] == staff.id
    assert (
        papeleria.json()["module_code"]
        == "PAPELERIA"
    )

    papeleria_session = client.get(
        "/pos/staff/session",
        headers={
            "Authorization":
                f"Bearer {papeleria.json()['access_token']}",
        },
    )

    assert papeleria_session.status_code == 200
    assert (
        papeleria_session.json()["module_code"]
        == "PAPELERIA"
    )
