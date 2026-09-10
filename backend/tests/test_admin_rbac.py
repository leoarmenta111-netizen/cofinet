from app.models.admin import Admin, AdminRole

import pytest
pytestmark = pytest.mark.usefixtures("default_branch")


class FakeMikroTik:
    @classmethod
    def for_branch(cls, _branch_code):
        return cls()

    def create_hotspot_user_strict(self, **_kwargs):
        return None

    def remove_hotspot_user(self, _username):
        return None

    def disconnect(self):
        return None


def test_existing_admin_is_super_and_can_view_dashboard(client, super_admin, super_headers):
    me = client.get("/admin/me", headers=super_headers)
    dashboard = client.get("/admin/dashboard", headers=super_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "super_admin"
    assert dashboard.status_code == 200
    assert "total_sales_month" in dashboard.json()


def test_operator_permissions_and_pin_audit(
    client, db_session, super_admin, super_headers, monkeypatch
):
    created = client.post(
        "/admin/accounts",
        headers=super_headers,
        json={
            "email": "cashier@example.com",
            "full_name": "Local Cashier",
            "password": "LocalCashierPass123!",
            "role": "pin_operator",
        },
    )
    assert created.status_code == 201

    login = client.post(
        "/admin/login",
        json={"email": "cashier@example.com", "password": "LocalCashierPass123!"},
    )
    assert login.status_code == 200
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/admin/dashboard", headers=operator_headers).status_code == 403
    assert client.get("/admin/payments", headers=operator_headers).status_code == 403
    assert client.get("/admin/accounts", headers=operator_headers).status_code == 403
    assert client.post(
        "/plans",
        headers=operator_headers,
        json={"name": "Forbidden", "price": 1, "duration_minutes": 1},
    ).status_code == 403

    monkeypatch.setattr("app.services.admin_service.MikroTikService", FakeMikroTik)
    plan_id = client.get("/plans").json()[0]["id"]
    super_pin = client.post(
        "/admin/pins", headers=super_headers, json={"plan_id": plan_id}
    )
    assert super_pin.status_code == 201
    pin_response = client.post(
        "/admin/pins", headers=operator_headers, json={"plan_id": plan_id}
    )
    assert pin_response.status_code == 201
    pin = pin_response.json()
    assert pin["creation_source"] == "admin_cash"
    assert pin["created_by_admin_id"] == created.json()["id"]

    own_pins = client.get("/admin/pins", headers=operator_headers)
    assert own_pins.status_code == 200
    assert len(own_pins.json()["pins"]) == 1
    assert client.post("/pins/validate", json={"pin": pin["pin"]}).status_code == 200


def test_disabled_admin_cannot_login(client, db_session, super_admin, super_headers):
    created = client.post(
        "/admin/accounts",
        headers=super_headers,
        json={
            "email": "disabled@example.com",
            "full_name": "Disabled Operator",
            "password": "DisabledLocalPass123!",
            "role": "pin_operator",
        },
    )
    admin_id = created.json()["id"]
    disabled = client.patch(
        f"/admin/accounts/{admin_id}/status",
        headers=super_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    login = client.post(
        "/admin/login",
        json={"email": "disabled@example.com", "password": "DisabledLocalPass123!"},
    )
    assert login.status_code == 403


def test_final_active_super_cannot_be_disabled_or_demoted(client, super_admin, super_headers):
    disabled = client.patch(
        f"/admin/accounts/{super_admin.id}/status",
        headers=super_headers,
        json={"is_active": False},
    )
    demoted = client.patch(
        f"/admin/accounts/{super_admin.id}/role",
        headers=super_headers,
        json={"role": "pin_operator"},
    )
    assert disabled.status_code == 409
    assert demoted.status_code == 409
