from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.branch import Branch
from app.models.pos_orders import PosOrder


def _models():
    from app.models.self_orders import (
        SelfOrder,
        SelfOrderDevice,
        SelfOrderItem,
        SelfOrderItemModifier,
        SelfOrderPaymentAttempt,
    )

    return (
        SelfOrder,
        SelfOrderDevice,
        SelfOrderItem,
        SelfOrderItemModifier,
        SelfOrderPaymentAttempt,
    )


@pytest.fixture()
def ixtapa_branch(db_session):
    branch = Branch(
        name="Ixtapa",
        code="ixtapa",
        is_active=True,
    )
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    return branch


def test_self_order_models_exist():
    (
        SelfOrder,
        SelfOrderDevice,
        SelfOrderItem,
        SelfOrderItemModifier,
        SelfOrderPaymentAttempt,
    ) = _models()

    assert SelfOrder.__tablename__ == "self_orders"
    assert SelfOrderDevice.__tablename__ == "self_order_devices"
    assert SelfOrderItem.__tablename__ == "self_order_items"
    assert SelfOrderItemModifier.__tablename__ == "self_order_item_modifiers"
    assert SelfOrderPaymentAttempt.__tablename__ == "self_order_payment_attempts"


def test_self_order_constraints_are_declared():
    (
        SelfOrder,
        SelfOrderDevice,
        SelfOrderItem,
        _,
        SelfOrderPaymentAttempt,
    ) = _models()

    constraint_names = {
        constraint.name
        for table in (
            SelfOrder.__table__,
            SelfOrderDevice.__table__,
            SelfOrderItem.__table__,
            SelfOrderPaymentAttempt.__table__,
        )
        for constraint in table.constraints
        if constraint.name
    }

    assert {
        "ck_self_order_devices_source",
        "ck_self_orders_status",
        "ck_self_orders_subtotal_nonnegative",
        "ck_self_orders_total_nonnegative",
        "ck_self_order_items_quantity_positive",
        "ck_self_order_payment_attempts_status",
        "ck_self_order_payment_attempts_amount_nonnegative",
    }.issubset(constraint_names)


def test_self_order_idempotency_columns_are_unique():
    (
        SelfOrder,
        SelfOrderDevice,
        _,
        _,
        SelfOrderPaymentAttempt,
    ) = _models()

    assert SelfOrder.__table__.c.self_order_uuid.unique is True
    assert SelfOrderDevice.__table__.c.device_code.unique is True
    assert (
        SelfOrderPaymentAttempt.__table__.c.payment_attempt_uuid.unique
        is True
    )


def test_pos_order_has_self_order_provenance_contract():
    assert "source" in PosOrder.__table__.c
    assert "self_order_id" in PosOrder.__table__.c
    assert PosOrder.__table__.c.source.default.arg == "POS"
    assert PosOrder.__table__.c.self_order_id.nullable is True
    assert PosOrder.__table__.c.self_order_id.unique is True

    constraint_names = {
        constraint.name
        for constraint in PosOrder.__table__.constraints
        if constraint.name
    }

    assert "ck_pos_orders_source" in constraint_names


def test_ixtapa_device_seed_is_idempotent_and_preserves_disabled(
    db_session,
    ixtapa_branch,
):
    from app.database.self_order_seed import ensure_self_order_devices

    (
        _,
        SelfOrderDevice,
        _,
        _,
        _,
    ) = _models()

    ensure_self_order_devices(db_session)
    ensure_self_order_devices(db_session)

    devices = (
        db_session.query(SelfOrderDevice)
        .order_by(SelfOrderDevice.device_code)
        .all()
    )

    assert [
        (device.device_code, device.source)
        for device in devices
    ] == [
        ("BAR-TABLET-IXTAPA-01", "BAR_TABLET"),
        ("KIOSK-IXTAPA-01", "KIOSK"),
    ]

    kiosk = next(
        device
        for device in devices
        if device.device_code == "KIOSK-IXTAPA-01"
    )
    kiosk.is_active = False
    db_session.commit()

    ensure_self_order_devices(db_session)

    db_session.refresh(kiosk)
    assert kiosk.is_active is False
