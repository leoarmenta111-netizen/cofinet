from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.auth.security import hash_password
from app.models.admin import Admin, AdminRole
from app.models.payment import Payment
from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from app.services.mikrotik_service import MikroTikUserExistsError
from app.services.payment_service import PaymentService


class RecordingMikroTik:
    calls: list[dict] = []
    removed: list[str] = []
    collision_once = False
    fail = False

    def __init__(self):
        pass

    @classmethod
    def reset(cls):
        cls.calls = []
        cls.removed = []
        cls.collision_once = False
        cls.fail = False

    def create_hotspot_user_strict(self, **kwargs):
        type(self).calls.append(kwargs)
        if type(self).collision_once and len(type(self).calls) == 1:
            raise MikroTikUserExistsError("simulated existing Hotspot user")
        if type(self).fail:
            raise RuntimeError("simulated MikroTik outage")

    def remove_hotspot_user(self, username):
        type(self).removed.append(username)

    def disconnect(self):
        return None


def create_operator(db_session, client):
    password = "OperatorPassword123!"
    operator = Admin(
        email="plan.operator@example.com",
        full_name="Plan Operator",
        password_hash=hash_password(password),
        role=AdminRole.PIN_OPERATOR,
        is_active=True,
    )
    db_session.add(operator)
    db_session.commit()
    response = client.post(
        "/admin/login", json={"email": operator.email, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def plan_id(client):
    return client.get("/plans").json()[0]["id"]


def test_super_admin_updates_each_catalogue_field_and_persists(
    client, db_session, super_admin, super_headers
):
    target = plan_id(client)

    price = client.patch(
        f"/admin/plans/{target}", headers=super_headers, json={"price": 26}
    )
    assert price.status_code == 200
    assert Decimal(price.json()["price"]) == Decimal("26.00")

    duration = client.patch(
        f"/admin/plans/{target}",
        headers=super_headers,
        json={"duration_minutes": 31},
    )
    assert duration.status_code == 200
    assert duration.json()["duration_minutes"] == 31

    both = client.patch(
        f"/admin/plans/{target}",
        headers=super_headers,
        json={"price": 27.5, "duration_minutes": 120},
    )
    assert both.status_code == 200
    db_session.expire_all()
    persisted = client.get(f"/plans/{target}").json()
    assert Decimal(persisted["price"]) == Decimal("27.50")
    assert persisted["duration_minutes"] == 120


def test_plan_update_authentication_authorization_and_not_found(
    client, db_session, super_admin, super_headers
):
    target = plan_id(client)
    operator_headers = create_operator(db_session, client)
    assert client.patch(f"/admin/plans/{target}", json={"price": 20}).status_code == 401
    assert client.patch(
        f"/admin/plans/{target}", headers=operator_headers, json={"price": 20}
    ).status_code == 403
    assert client.patch(
        "/admin/plans/999999", headers=super_headers, json={"price": 20}
    ).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"price": -1},
        {"duration_minutes": 0},
        {"duration_minutes": -1},
        {"price": "not-a-number"},
        {"price": "NaN"},
        {"price": "Infinity"},
        {"duration_minutes": "invalid"},
        {"duration_minutes": 1.5},
        {"price": None},
        {"duration_minutes": None},
        {},
    ],
)
def test_plan_update_rejects_invalid_values(
    payload, client, super_admin, super_headers
):
    response = client.patch(
        f"/admin/plans/{plan_id(client)}", headers=super_headers, json=payload
    )
    assert response.status_code == 422


def test_plan_update_does_not_change_existing_purchase_or_pin_details(
    client, db_session, super_admin, super_headers
):
    target = plan_id(client)
    issued = datetime.now(UTC)
    purchase = Purchase(
        plan_id=target,
        amount=Decimal("25.00"),
        status=PurchaseStatus.PAID,
        pin_code="456789",
        issued_at=issued,
        expires_at=issued + timedelta(minutes=30),
        creation_source=PurchaseCreationSource.ADMIN_CASH,
        created_by_admin_id=super_admin.id,
    )
    db_session.add(purchase)
    db_session.commit()
    original_expiry = purchase.expires_at

    response = client.patch(
        f"/admin/plans/{target}",
        headers=super_headers,
        json={"price": 99, "duration_minutes": 1440},
    )
    assert response.status_code == 200
    db_session.refresh(purchase)
    assert purchase.amount == Decimal("25.00")
    assert purchase.expires_at.replace(tzinfo=UTC) == original_expiry
    validation = client.post("/pins/validate", json={"pin": "456789"})
    assert validation.status_code == 200
    assert validation.json()["minutes"] == 30


def test_new_cash_pin_uses_updated_plan_and_mikrotik_contract(
    client, db_session, super_admin, super_headers, monkeypatch
):
    RecordingMikroTik.reset()
    monkeypatch.setattr("app.services.admin_service.MikroTikService", RecordingMikroTik)
    monkeypatch.setattr(
        "app.services.admin_service.AdminService._generate_pin", lambda: "345678"
    )
    target = plan_id(client)
    client.patch(
        f"/admin/plans/{target}",
        headers=super_headers,
        json={"price": 48.5, "duration_minutes": 90},
    )

    response = client.post(
        "/admin/pins", headers=super_headers, json={"plan_id": target}
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("48.50")
    assert body["duration_minutes"] == 90
    assert datetime.fromisoformat(body["expires_at"]) - datetime.fromisoformat(
        body["issued_at"]
    ) == timedelta(minutes=90)
    assert RecordingMikroTik.calls == [
        {
            "username": "345678",
            "password": "345678",
            "duration_minutes": 90,
            "profile": "default",
            "comment": "CofiNet cash purchase",
        }
    ]
    purchase = db_session.scalar(select(Purchase).where(Purchase.pin_code == "345678"))
    assert purchase is not None and purchase.plan_id == target
    assert client.post("/pins/validate", json={"pin": "345678"}).json()["valid"] is True


def test_mikrotik_failure_returns_error_without_paid_purchase(
    client, db_session, super_admin, super_headers, monkeypatch
):
    RecordingMikroTik.reset()
    RecordingMikroTik.fail = True
    monkeypatch.setattr("app.services.admin_service.MikroTikService", RecordingMikroTik)
    monkeypatch.setattr(
        "app.services.admin_service.AdminService._generate_pin", lambda: "234567"
    )
    response = client.post(
        "/admin/pins", headers=super_headers, json={"plan_id": plan_id(client)}
    )
    assert response.status_code == 502
    assert db_session.scalar(
        select(Purchase).where(Purchase.pin_code == "234567")
    ) is None


def test_mikrotik_collision_retries_without_duplicate_purchase(
    client, db_session, super_admin, super_headers, monkeypatch
):
    RecordingMikroTik.reset()
    RecordingMikroTik.collision_once = True
    generated = iter(["654321", "654323"])
    monkeypatch.setattr("app.services.admin_service.MikroTikService", RecordingMikroTik)
    monkeypatch.setattr(
        "app.services.admin_service.AdminService._generate_pin", lambda: next(generated)
    )
    response = client.post(
        "/admin/pins", headers=super_headers, json={"plan_id": plan_id(client)}
    )
    assert response.status_code == 201
    assert response.json()["pin"] == "654323"
    assert [call["username"] for call in RecordingMikroTik.calls] == ["654321", "654323"]
    assert db_session.scalar(select(Purchase).where(Purchase.pin_code == "654321")) is None


def create_pending_payment(db_session, target, amount=Decimal("25.00")):
    purchase = Purchase(
        plan_id=target,
        amount=amount,
        status=PurchaseStatus.PENDING,
        creation_source=PurchaseCreationSource.MERCADOPAGO,
    )
    db_session.add(purchase)
    db_session.flush()
    payment = Payment(
        purchase_id=purchase.id,
        provider="mercadopago",
        provider_preference_id=f"pref-{purchase.id}",
        amount=amount,
        currency="MXN",
        status="pending",
    )
    db_session.add(payment)
    db_session.commit()
    return purchase, payment


def test_mercadopago_approval_commits_pin_only_after_mikrotik_success(
    client, db_session, super_admin, super_headers, monkeypatch
):
    RecordingMikroTik.reset()
    target = plan_id(client)
    client.patch(
        f"/admin/plans/{target}",
        headers=super_headers,
        json={"price": 55, "duration_minutes": 120},
    )
    purchase, payment = create_pending_payment(db_session, target, Decimal("55.00"))
    monkeypatch.setattr("app.services.purchase_service.MikroTikService", RecordingMikroTik)
    monkeypatch.setattr(
        "app.services.purchase_service.PurchaseService._generate_pin", lambda: "567890"
    )
    monkeypatch.setattr(
        PaymentService,
        "_get_mercadopago_payment",
        lambda _payment_id: {
            "id": "provider-1",
            "status": "approved",
            "external_reference": str(purchase.id),
        },
    )

    PaymentService.process_mercadopago_webhook(db_session, {"data": {"id": "provider-1"}})
    db_session.refresh(purchase)
    db_session.refresh(payment)
    assert purchase.status == PurchaseStatus.PAID
    assert purchase.pin_code == "567890"
    assert purchase.amount == Decimal("55.00")
    assert purchase.expires_at - purchase.issued_at == timedelta(minutes=120)
    assert payment.status == "approved"
    assert RecordingMikroTik.calls[0]["profile"] == "default"
    assert RecordingMikroTik.calls[0]["duration_minutes"] == 120


def test_mercadopago_mikrotik_failure_rolls_back_payment_and_purchase(
    client, db_session, super_admin, monkeypatch
):
    RecordingMikroTik.reset()
    RecordingMikroTik.fail = True
    purchase, payment = create_pending_payment(db_session, plan_id(client))
    monkeypatch.setattr("app.services.purchase_service.MikroTikService", RecordingMikroTik)
    monkeypatch.setattr(
        "app.services.purchase_service.PurchaseService._generate_pin", lambda: "678901"
    )
    monkeypatch.setattr(
        PaymentService,
        "_get_mercadopago_payment",
        lambda _payment_id: {
            "id": "provider-2",
            "status": "approved",
            "external_reference": str(purchase.id),
        },
    )

    with pytest.raises(Exception):
        PaymentService.process_mercadopago_webhook(
            db_session, {"data": {"id": "provider-2"}}
        )
    db_session.refresh(purchase)
    db_session.refresh(payment)
    assert purchase.status == PurchaseStatus.PENDING
    assert purchase.pin_code is None
    assert purchase.issued_at is None
    assert purchase.expires_at is None
    assert payment.status == "pending"
