from app.auth.security import hash_password, verify_password
from app.models.admin import Admin, AdminRole
from app.models.branch import Branch
from app.models.pos_staff import PosStaff


def _create_branch(db_session):
    branch = Branch(
        name="CofiCenter Ixtapa",
        code="ixtapa",
        is_active=True,
    )
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    return branch


def test_super_admin_can_create_pos_staff_without_exposing_pin(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Caja Ixtapa",
            "role": "CASHIER",
            "pin": "2468",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] > 0
    assert body["branch_id"] == branch.id
    assert body["branch_code"] == "ixtapa"
    assert body["display_name"] == "Caja Ixtapa"
    assert body["role"] == "CASHIER"
    assert body["is_active"] is True

    assert "pin" not in body
    assert "pin_hash" not in body

    staff = db_session.get(
        PosStaff,
        body["id"],
    )

    assert staff is not None
    assert staff.pin_hash != "2468"
    assert verify_password(
        "2468",
        staff.pin_hash,
    )



def _pin_operator_headers(
    client,
    db_session,
):
    password = "PinOperatorPass123!"

    admin = Admin(
        email="pin-operator@example.com",
        password_hash=hash_password(password),
        full_name="PIN Operator",
        role=AdminRole.PIN_OPERATOR,
        is_active=True,
    )

    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    response = client.post(
        "/admin/login",
        json={
            "email": admin.email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization":
            f"Bearer {response.json()['access_token']}"
    }


def test_pin_operator_cannot_create_pos_staff(
    client,
    db_session,
):
    branch = _create_branch(db_session)
    headers = _pin_operator_headers(
        client,
        db_session,
    )

    response = client.post(
        "/admin/pos/staff",
        headers=headers,
        json={
            "branch_id": branch.id,
            "display_name": "Unauthorized Staff",
            "role": "MANAGER",
            "pin": "1357",
        },
    )

    assert response.status_code == 403

    staff = (
        db_session.query(PosStaff)
        .filter(
            PosStaff.display_name
            == "Unauthorized Staff"
        )
        .one_or_none()
    )

    assert staff is None


def test_super_admin_can_list_pos_staff_without_pin_data(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    create_response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Leonardo Caja",
            "role": "MANAGER",
            "pin": "8642",
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        "/admin/pos/staff",
        headers=super_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) == 1

    staff = body[0]

    assert staff["id"] == create_response.json()["id"]
    assert staff["branch_id"] == branch.id
    assert staff["branch_code"] == "ixtapa"
    assert staff["display_name"] == "Leonardo Caja"
    assert staff["role"] == "MANAGER"
    assert staff["is_active"] is True

    assert "pin" not in staff
    assert "pin_hash" not in staff


def test_super_admin_can_update_and_deactivate_pos_staff(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    create_response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Caja Temporal",
            "role": "CASHIER",
            "pin": "2468",
        },
    )

    assert create_response.status_code == 201
    staff_id = create_response.json()["id"]

    response = client.patch(
        f"/admin/pos/staff/{staff_id}",
        headers=super_headers,
        json={
            "display_name": "Gerente Ixtapa",
            "role": "MANAGER",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == staff_id
    assert body["branch_id"] == branch.id
    assert body["branch_code"] == "ixtapa"
    assert body["display_name"] == "Gerente Ixtapa"
    assert body["role"] == "MANAGER"
    assert body["is_active"] is False
    assert "pin" not in body
    assert "pin_hash" not in body

    staff = db_session.get(PosStaff, staff_id)

    assert staff.display_name == "Gerente Ixtapa"
    assert staff.role == "MANAGER"
    assert staff.is_active is False


def test_super_admin_can_reset_pos_staff_pin(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    create_response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Caja PIN",
            "role": "CASHIER",
            "pin": "2468",
        },
    )

    assert create_response.status_code == 201
    staff_id = create_response.json()["id"]

    reset_response = client.post(
        f"/admin/pos/staff/{staff_id}/reset-pin",
        headers=super_headers,
        json={
            "pin": "9753",
        },
    )

    assert reset_response.status_code == 200

    body = reset_response.json()

    assert body["id"] == staff_id
    assert body["display_name"] == "Caja PIN"
    assert "pin" not in body
    assert "pin_hash" not in body

    old_pin_response = client.post(
        "/pos/staff/unlock",
        json={
            "staff_id": staff_id,
            "pin": "2468",
            "branch_code": "ixtapa",
            "terminal_id": "ixtapa-register-1",
        },
    )

    assert old_pin_response.status_code == 401

    new_pin_response = client.post(
        "/pos/staff/unlock",
        json={
            "staff_id": staff_id,
            "pin": "9753",
            "branch_code": "ixtapa",
            "terminal_id": "ixtapa-register-1",
        },
    )

    assert new_pin_response.status_code == 200
    assert (
        new_pin_response.json()["staff_id"]
        == staff_id
    )


def test_pin_operator_cannot_reset_pos_staff_pin(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    create_response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Caja Protegida",
            "role": "CASHIER",
            "pin": "2468",
        },
    )

    assert create_response.status_code == 201
    staff_id = create_response.json()["id"]

    headers = _pin_operator_headers(
        client,
        db_session,
    )

    response = client.post(
        f"/admin/pos/staff/{staff_id}/reset-pin",
        headers=headers,
        json={
            "pin": "9999",
        },
    )

    assert response.status_code == 403

    staff = db_session.get(
        PosStaff,
        staff_id,
    )

    assert verify_password(
        "2468",
        staff.pin_hash,
    )

    assert not verify_password(
        "9999",
        staff.pin_hash,
    )


def test_deactivated_pos_staff_cannot_unlock_pos(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session)

    create_response = client.post(
        "/admin/pos/staff",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "display_name": "Caja Desactivada",
            "role": "CASHIER",
            "pin": "2468",
        },
    )

    assert create_response.status_code == 201
    staff_id = create_response.json()["id"]

    update_response = client.patch(
        f"/admin/pos/staff/{staff_id}",
        headers=super_headers,
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200
    assert (
        update_response.json()["is_active"]
        is False
    )

    unlock_response = client.post(
        "/pos/staff/unlock",
        json={
            "staff_id": staff_id,
            "pin": "2468",
            "branch_code": "ixtapa",
            "terminal_id": "ixtapa-register-1",
        },
    )

    assert unlock_response.status_code == 403
