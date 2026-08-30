from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.pos_customers import (
    Customer,
    LoyaltyLedgerEntry,
)


def test_customer_phone_normalized_is_unique(
    db_session,
):
    first = Customer(
        customer_uuid="11111111-1111-1111-1111-111111111111",
        name="María López",
        phone="322 123 4567",
        phone_normalized="+523221234567",
    )

    second = Customer(
        customer_uuid="22222222-2222-2222-2222-222222222222",
        name="Maria Lopez 2",
        phone="+52 322 123 4567",
        phone_normalized="+523221234567",
    )

    db_session.add(first)
    db_session.commit()

    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_customer_optional_profile_fields(
    db_session,
):
    customer = Customer(
        customer_uuid="33333333-3333-3333-3333-333333333333",
        name="Ana Pérez",
        phone="3221112233",
        phone_normalized="+523221112233",
        email="ana@example.com",
        birthday=date(1995, 5, 14),
    )

    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    assert customer.email == "ana@example.com"
    assert customer.birthday == date(
        1995,
        5,
        14,
    )


def test_loyalty_idempotency_key_is_unique(
    db_session,
):
    customer = Customer(
        customer_uuid="44444444-4444-4444-4444-444444444444",
        name="Cliente Ledger",
        phone="3222223344",
        phone_normalized="+523222223344",
    )

    db_session.add(customer)
    db_session.flush()

    first = LoyaltyLedgerEntry(
        entry_uuid="55555555-5555-5555-5555-555555555555",
        customer_id=customer.id,
        points=10,
        entry_type="EARN",
        idempotency_key="EARN:test-order",
    )

    second = LoyaltyLedgerEntry(
        entry_uuid="66666666-6666-6666-6666-666666666666",
        customer_id=customer.id,
        points=10,
        entry_type="EARN",
        idempotency_key="EARN:test-order",
    )

    db_session.add(first)
    db_session.commit()

    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()


from app.models.pos_orders import PosOrder


def test_pos_order_has_optional_customer_fk():
    column = PosOrder.__table__.c.customer_id

    assert column.nullable is True

    targets = {
        foreign_key.target_fullname
        for foreign_key in column.foreign_keys
    }

    assert "pos_customers.id" in targets


from app.services.pos_customer_service import (
    normalize_customer_phone,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "3221234567",
            "+523221234567",
        ),
        (
            "322 123 4567",
            "+523221234567",
        ),
        (
            "322-123-4567",
            "+523221234567",
        ),
        (
            "+52 322 123 4567",
            "+523221234567",
        ),
        (
            "52 322 123 4567",
            "+523221234567",
        ),
    ],
)
def test_normalize_mexican_customer_phone(
    raw,
    expected,
):
    assert (
        normalize_customer_phone(raw)
        == expected
    )


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "123",
        "abcdef",
    ],
)
def test_invalid_customer_phone_is_rejected(
    raw,
):
    with pytest.raises(ValueError):
        normalize_customer_phone(raw)


from app.services.pos_customer_service import (
    PosCustomerService,
)


def test_customer_service_deduplicates_by_phone(
    db_session,
):
    first = PosCustomerService.create(
        db_session,
        name="María López",
        phone="322 123 4567",
    )

    second = PosCustomerService.create(
        db_session,
        name="Otra María",
        phone="+52 322 123 4567",
    )

    assert first.id == second.id
    assert first.customer_uuid == second.customer_uuid

    customers = (
        db_session.query(Customer)
        .all()
    )

    assert len(customers) == 1


def test_customer_service_normalizes_profile(
    db_session,
):
    customer = PosCustomerService.create(
        db_session,
        name="  Ana Pérez  ",
        phone="3221112233",
        email="  ANA@EXAMPLE.COM  ",
        birthday=date(1995, 5, 14),
    )

    assert customer.name == "Ana Pérez"
    assert customer.phone_normalized == "+523221112233"
    assert customer.email == "ana@example.com"
    assert customer.birthday == date(
        1995,
        5,
        14,
    )


def test_admin_can_create_customer(
    client,
    super_headers,
    db_session,
):
    response = client.post(
        "/admin/pos/customers",
        headers=super_headers,
        json={
            "name": "María López",
            "phone": "322 123 4567",
            "email": "MARIA@EXAMPLE.COM",
            "birthday": "1995-05-14",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "María López"
    assert data["phone_normalized"] == "+523221234567"
    assert data["email"] == "maria@example.com"
    assert data["birthday"] == "1995-05-14"

    customer = (
        db_session.query(Customer)
        .filter(
            Customer.phone_normalized
            == "+523221234567"
        )
        .one()
    )

    assert customer.customer_uuid == data["customer_uuid"]


def test_admin_can_search_customer_by_phone(
    client,
    super_headers,
    db_session,
):
    PosCustomerService.create(
        db_session,
        name="María López",
        phone="322 123 4567",
    )
    PosCustomerService.create(
        db_session,
        name="Carlos Rivera",
        phone="322 999 8877",
    )
    db_session.commit()

    response = client.get(
        "/admin/pos/customers",
        headers=super_headers,
        params={
            "q": "3221234567",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "María López"
    assert (
        data[0]["phone_normalized"]
        == "+523221234567"
    )


def test_admin_can_search_customer_by_name(
    client,
    super_headers,
    db_session,
):
    PosCustomerService.create(
        db_session,
        name="María López",
        phone="322 123 4567",
    )
    PosCustomerService.create(
        db_session,
        name="Carlos Rivera",
        phone="322 999 8877",
    )
    db_session.commit()

    response = client.get(
        "/admin/pos/customers",
        headers=super_headers,
        params={
            "q": "María",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "María López"


def test_admin_can_get_customer_by_uuid(
    client,
    super_headers,
    db_session,
):
    customer = PosCustomerService.create(
        db_session,
        name="María López",
        phone="322 123 4567",
    )
    db_session.commit()

    response = client.get(
        f"/admin/pos/customers/{customer.customer_uuid}",
        headers=super_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["customer_uuid"] == customer.customer_uuid
    assert data["name"] == "María López"
    assert data["phone_normalized"] == "+523221234567"
