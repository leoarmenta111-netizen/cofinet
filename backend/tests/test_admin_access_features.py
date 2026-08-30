from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import uuid4

from sqlalchemy import func, select

from app.auth.security import hash_password
from app.models.admin import Admin, AdminRole
from app.models.admin_access import (
    InternalHotspotCredential,
    PinBatch,
    PinBatchStatus,
)
from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from app.services.mikrotik_service import MikroTikUserExistsError

import pytest
pytestmark = pytest.mark.usefixtures("default_branch")


class RecordingMikroTik:
    @classmethod
    def for_branch(cls, _branch_code):
        return cls()

    users: set[str] = set()
    standard_attempts: list[str] = []
    permanent_attempts: list[str] = []
    removed: list[str] = []
    disabled_changes: list[tuple[str, bool]] = []
    fail_standard_at: set[int] = set()

    def __init__(self):
        pass

    @classmethod
    def reset(cls):
        cls.users = set()
        cls.standard_attempts = []
        cls.permanent_attempts = []
        cls.removed = []
        cls.disabled_changes = []
        cls.fail_standard_at = set()

    def create_hotspot_user_strict(self, username, **_kwargs):
        self.standard_attempts.append(username)
        if len(self.standard_attempts) in self.fail_standard_at:
            raise RuntimeError("simulated MikroTik failure")
        if username in self.users:
            raise MikroTikUserExistsError("exists")
        self.users.add(username)

    def create_permanent_hotspot_user_strict(self, username, **_kwargs):
        self.permanent_attempts.append(username)
        if username in self.users:
            raise MikroTikUserExistsError("exists")
        self.users.add(username)

    def set_hotspot_user_disabled(self, username, disabled):
        type(self).disabled_changes.append((username, disabled))
        return username in self.users

    def remove_hotspot_user(self, username):
        self.removed.append(username)
        self.users.discard(username)

    def disconnect(self):
        return None


def deterministic_pins(start=100000):
    values = count(start)
    return lambda: f"{next(values):06d}"


def create_operator(db_session, client, email, name):
    password = "OperatorPassword123!"
    admin = Admin(
        email=email,
        full_name=name,
        password_hash=hash_password(password),
        role=AdminRole.PIN_OPERATOR,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    login = client.post("/admin/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return admin, {"Authorization": f"Bearer {login.json()['access_token']}"}


def install_recording_mikrotik(monkeypatch):
    RecordingMikroTik.reset()
    monkeypatch.setattr(
        "app.services.admin_access_service.MikroTikService", RecordingMikroTik
    )


class OfflineMikroTik:
    @classmethod
    def for_branch(cls, _branch_code):
        return cls()

    connection_attempts = 0

    def __init__(self):
        type(self).connection_attempts += 1
        raise RuntimeError("MikroTik is offline")


def test_read_only_history_works_with_mikrotik_offline(
    client, db_session, super_admin, super_headers, monkeypatch
):
    OfflineMikroTik.connection_attempts = 0
    monkeypatch.setattr(
        "app.services.admin_access_service.MikroTikService", OfflineMikroTik
    )

    empty_batches = client.get("/admin/pin-batches", headers=super_headers)
    empty_internal = client.get("/admin/internal-access", headers=super_headers)
    assert empty_batches.status_code == 200
    assert empty_batches.json() == {"batches": []}
    assert empty_internal.status_code == 200
    assert empty_internal.json() == {"credentials": []}

    plan_id = client.get("/plans").json()[0]["id"]
    batch = PinBatch(
        batch_uuid=str(uuid4()),
        request_uuid=str(uuid4()),
        plan_id=plan_id,
        requested_quantity=1,
        created_quantity=1,
        failed_quantity=0,
        status=PinBatchStatus.COMPLETED,
        created_by_admin_id=super_admin.id,
        completed_at=datetime.now(UTC),
    )
    db_session.add(batch)
    db_session.flush()
    issued_at = datetime.now(UTC)
    db_session.add(
        Purchase(
            plan_id=plan_id,
            amount=25,
            status=PurchaseStatus.PAID,
            pin_code="654321",
            issued_at=issued_at,
            expires_at=issued_at + timedelta(minutes=30),
            creation_source=PurchaseCreationSource.ADMIN_BATCH,
            created_by_admin_id=super_admin.id,
            pin_batch_id=batch.id,
        )
    )
    db_session.add(
        InternalHotspotCredential(
            request_uuid=str(uuid4()),
            label="Offline history tablet",
            pin_code="765432",
            creation_source="internal_device",
            is_active=True,
            created_by_admin_id=super_admin.id,
        )
    )
    db_session.commit()

    batch_list = client.get("/admin/pin-batches", headers=super_headers)
    batch_detail = client.get(
        f"/admin/pin-batches/{batch.id}", headers=super_headers
    )
    print_data = client.get(
        f"/admin/pin-batches/{batch.id}/print-data", headers=super_headers
    )
    internal_list = client.get("/admin/internal-access", headers=super_headers)

    assert batch_list.status_code == 200
    assert [item["id"] for item in batch_list.json()["batches"]] == [batch.id]
    assert batch_detail.status_code == 200
    assert [item["pin"] for item in batch_detail.json()["pins"]] == ["654321"]
    assert print_data.status_code == 200
    assert [item["pin"] for item in print_data.json()["tickets"]] == ["654321"]
    assert internal_list.status_code == 200
    assert [item["pin"] for item in internal_list.json()["credentials"]] == [
        "765432"
    ]
    assert OfflineMikroTik.connection_attempts == 0


def test_super_admin_generates_100_unique_batch_pins_and_reprints_without_regeneration(
    client, db_session, super_admin, super_headers, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        deterministic_pins(),
    )
    plan_id = client.get("/plans").json()[0]["id"]
    request_id = str(uuid4())
    response = client.post(
        "/admin/pin-batches",
        headers=super_headers,
        json={"plan_id": plan_id, "quantity": 100, "request_id": request_id},
    )
    assert response.status_code == 201
    batch = response.json()
    assert (batch["requested"], batch["created"], batch["failed"]) == (100, 100, 0)
    assert len({item["pin"] for item in batch["pins"]}) == 100
    assert len(RecordingMikroTik.standard_attempts) == 100

    purchases = db_session.execute(
        select(Purchase).where(
            Purchase.creation_source == PurchaseCreationSource.ADMIN_BATCH
        )
    ).scalars().all()
    assert len(purchases) == 100
    assert all(item.pin_batch_id == batch["id"] for item in purchases)

    print_data = client.get(
        f"/admin/pin-batches/{batch['id']}/print-data", headers=super_headers
    )
    assert print_data.status_code == 200
    assert len(print_data.json()["tickets"]) == 100
    assert db_session.scalar(select(func.count(Purchase.id))) == 100

    replay = client.post(
        "/admin/pin-batches",
        headers=super_headers,
        json={"plan_id": plan_id, "quantity": 100, "request_id": request_id},
    )
    assert replay.status_code == 201
    assert replay.json()["batch_uuid"] == batch["batch_uuid"]
    assert db_session.scalar(select(func.count(Purchase.id))) == 100
    assert len(RecordingMikroTik.standard_attempts) == 100


def test_duplicate_pin_collision_is_retried_before_mikrotik(
    client, db_session, super_admin, super_headers, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    plan_id = client.get("/plans").json()[0]["id"]
    db_session.add(
        Purchase(
            plan_id=plan_id,
            amount=25,
            status=PurchaseStatus.PAID,
            pin_code="100000",
            creation_source=PurchaseCreationSource.SYSTEM,
        )
    )
    db_session.commit()
    generated = iter(["100000", "100001"])
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        lambda: next(generated),
    )
    response = client.post(
        "/admin/pin-batches",
        headers=super_headers,
        json={"plan_id": plan_id, "quantity": 1, "request_id": str(uuid4())},
    )
    assert response.status_code == 201
    assert response.json()["pins"][0]["pin"] == "100001"
    assert RecordingMikroTik.standard_attempts == ["100001"]


def test_partial_mikrotik_failure_is_recorded_and_returns_502(
    client, super_admin, super_headers, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    RecordingMikroTik.fail_standard_at = {2}
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        deterministic_pins(),
    )
    plan_id = client.get("/plans").json()[0]["id"]
    response = client.post(
        "/admin/pin-batches",
        headers=super_headers,
        json={"plan_id": plan_id, "quantity": 3, "request_id": str(uuid4())},
    )
    assert response.status_code == 502
    batch = response.json()["batch"]
    assert (batch["requested"], batch["created"], batch["failed"]) == (3, 2, 1)
    assert batch["status"] == "partial"
    assert len(batch["pins"]) == 2
    assert batch["failures"][0]["error_code"] == "mikrotik_create_failed"


def test_operator_can_only_view_and_print_own_batches(
    client, db_session, super_admin, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        deterministic_pins(),
    )
    first, first_headers = create_operator(
        db_session, client, "first.operator@example.com", "First Operator"
    )
    _second, second_headers = create_operator(
        db_session, client, "second.operator@example.com", "Second Operator"
    )
    plan_id = client.get("/plans").json()[0]["id"]
    created = client.post(
        "/admin/pin-batches",
        headers=first_headers,
        json={"plan_id": plan_id, "quantity": 2, "request_id": str(uuid4())},
    )
    assert created.status_code == 201
    assert created.json()["created_by_admin_id"] == first.id
    assert len(client.get("/admin/pin-batches", headers=first_headers).json()["batches"]) == 1
    assert client.get("/admin/pin-batches", headers=second_headers).json()["batches"] == []
    batch_id = created.json()["id"]
    assert client.get(f"/admin/pin-batches/{batch_id}", headers=second_headers).status_code == 403
    assert client.get(
        f"/admin/pin-batches/{batch_id}/print-data", headers=second_headers
    ).status_code == 403


def test_permanent_internal_access_is_super_only_non_revenue_and_revocable(
    client, db_session, super_admin, super_headers, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        deterministic_pins(700000),
    )
    _operator, operator_headers = create_operator(
        db_session, client, "tablet.operator@example.com", "Tablet Operator"
    )
    request = {"label": "Tablet Pedidos 1", "request_id": str(uuid4())}
    assert client.post("/admin/internal-access", headers=operator_headers, json=request).status_code == 403
    assert client.get("/admin/internal-access", headers=operator_headers).status_code == 403

    before_purchases = db_session.scalar(select(func.count(Purchase.id)))
    first = client.post("/admin/internal-access", headers=super_headers, json=request)
    second = client.post(
        "/admin/internal-access",
        headers=super_headers,
        json={"label": "Tablet Pedidos 2", "request_id": str(uuid4())},
    )
    assert first.status_code == second.status_code == 201
    for response in (first, second):
        credential = response.json()
        assert credential["permanent"] is True
        assert credential["non_revenue"] is True
        assert credential["creation_source"] == "internal_device"
        assert credential["expires_at"] is None
    assert db_session.scalar(select(func.count(Purchase.id))) == before_purchases
    assert db_session.scalar(select(func.count(InternalHotspotCredential.id))) == 2
    assert len(RecordingMikroTik.permanent_attempts) == 2

    credential_id = first.json()["id"]
    pin = first.json()["pin"]
    revoked = client.patch(
        f"/admin/internal-access/{credential_id}/status",
        headers=super_headers,
        json={"is_active": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False
    assert revoked.json()["revoked_at"] is not None
    assert (pin, True) in RecordingMikroTik.disabled_changes
    assert pin in RecordingMikroTik.users
    assert pin not in RecordingMikroTik.removed


def test_internal_credentials_do_not_change_purchase_dashboard_counts(
    client, db_session, super_admin, super_headers, monkeypatch
):
    install_recording_mikrotik(monkeypatch)
    monkeypatch.setattr(
        "app.services.admin_access_service.AdminAccessService._generate_pin",
        deterministic_pins(800000),
    )
    before = client.get("/admin/dashboard", headers=super_headers).json()
    response = client.post(
        "/admin/internal-access",
        headers=super_headers,
        json={"label": "Metrics-free tablet", "request_id": str(uuid4())},
    )
    assert response.status_code == 201
    after = client.get("/admin/dashboard", headers=super_headers).json()
    assert after == before
    assert db_session.scalar(select(func.count(PinBatch.id))) == 0
