from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosModifierGroup,
    PosProduct,
    PosProductModifierGroup,
)
from app.models.self_orders import (
    SelfOrder,
    SelfOrderDevice,
)


def _schemas():
    from app.schemas.self_orders import (
        SelfOrderCreate,
        SelfOrderItemCreate,
    )

    return SelfOrderCreate, SelfOrderItemCreate


def _service():
    from app.services.self_order_service import SelfOrderService

    return SelfOrderService


def _seed(
    db_session,
    *,
    device_source='KIOSK',
    device_active=True,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f'Self Order Branch {suffix}',
        code=f'self-order-{suffix}',
        is_active=True,
    )

    category = PosCategory(
        name=f'Coffee {suffix}',
        slug=f'coffee-{suffix}',
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f'Latte {suffix}',
        base_price=Decimal('50.00'),
        preparation_station='BAR',
        is_active=True,
    )

    db_session.add(product)
    db_session.flush()

    branch_product = PosBranchProduct(
        branch_id=branch.id,
        product_id=product.id,
        price=Decimal('57.00'),
        is_available=True,
    )

    device = SelfOrderDevice(
        device_code=f'DEVICE-{suffix}',
        branch_id=branch.id,
        source=device_source,
        is_active=device_active,
    )

    db_session.add_all([
        branch_product,
        device,
    ])

    db_session.commit()

    for row in (
        branch,
        category,
        product,
        branch_product,
        device,
    ):
        db_session.refresh(row)

    return {
        'branch': branch,
        'category': category,
        'product': product,
        'branch_product': branch_product,
        'device': device,
    }


def _payload(
    data,
    *,
    self_order_uuid=None,
    device_code=None,
    quantity=1,
):
    SelfOrderCreate, _ = _schemas()

    return SelfOrderCreate(
        self_order_uuid=(
            self_order_uuid or uuid4()
        ),
        branch_code=data['branch'].code,
        device_code=(
            device_code
            or data['device'].device_code
        ),
        items=[
            {
                'product_id': data['product'].id,
                'quantity': quantity,
                'modifier_option_ids': [],
                'notes': None,
            }
        ],
    )


def test_create_schema_has_no_client_authoritative_fields():
    SelfOrderCreate, SelfOrderItemCreate = _schemas()

    assert set(
        SelfOrderCreate.model_fields
    ) == {
        'self_order_uuid',
        'branch_code',
        'device_code',
        'items',
    }

    assert set(
        SelfOrderItemCreate.model_fields
    ) == {
        'product_id',
        'quantity',
        'modifier_option_ids',
        'notes',
    }

    forbidden = {
        'source',
        'status',
        'subtotal',
        'total',
        'currency',
        'price',
        'unit_price',
        'line_total',
        'preparation_station',
        'payment_status',
    }

    assert not (
        forbidden
        & set(SelfOrderCreate.model_fields)
    )

    assert not (
        forbidden
        & set(SelfOrderItemCreate.model_fields)
    )


def test_create_uses_server_price_and_device_source(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    before = datetime.now(timezone.utc)

    created = SelfOrderService.create(
        db=db_session,
        payload=_payload(
            data,
            quantity=2,
        ),
    )

    after = datetime.now(timezone.utc)

    assert created.status == 'AWAITING_PAYMENT'
    assert created.branch_id == data['branch'].id
    assert created.device_id == data['device'].id
    assert created.device.source == 'KIOSK'

    assert Decimal(created.subtotal) == Decimal('114.00')
    assert Decimal(created.total) == Decimal('114.00')
    assert created.currency == 'MXN'

    assert len(created.items) == 1

    item = created.items[0]

    assert item.product_id == data['product'].id
    assert item.product_name == data['product'].name
    assert item.preparation_station == 'BAR'
    assert item.quantity == 2
    assert Decimal(item.unit_base_price) == Decimal('57.00')
    assert Decimal(item.unit_modifier_total) == Decimal('0.00')
    assert Decimal(item.unit_price) == Decimal('57.00')
    assert Decimal(item.line_total) == Decimal('114.00')

    assert (
        before + timedelta(minutes=29, seconds=59)
        <= created.expires_at
        <= after + timedelta(minutes=30, seconds=1)
    )


def test_same_uuid_same_branch_and_device_is_idempotent(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    order_uuid = uuid4()

    first = SelfOrderService.create(
        db=db_session,
        payload=_payload(
            data,
            self_order_uuid=order_uuid,
            quantity=1,
        ),
    )

    retry = SelfOrderService.create(
        db=db_session,
        payload=_payload(
            data,
            self_order_uuid=order_uuid,
            quantity=3,
        ),
    )

    assert retry.id == first.id
    assert retry.self_order_uuid == first.self_order_uuid
    assert Decimal(retry.total) == Decimal('57.00')
    assert retry.items[0].quantity == 1

    count = (
        db_session.query(SelfOrder)
        .filter(
            SelfOrder.self_order_uuid
            == str(order_uuid)
        )
        .count()
    )

    assert count == 1


def test_same_uuid_different_device_is_conflict(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    order_uuid = uuid4()

    SelfOrderService.create(
        db=db_session,
        payload=_payload(
            data,
            self_order_uuid=order_uuid,
        ),
    )

    second_device = SelfOrderDevice(
        device_code=f'OTHER-{uuid4().hex[:8]}',
        branch_id=data['branch'].id,
        source='BAR_TABLET',
        is_active=True,
    )

    db_session.add(second_device)
    db_session.commit()
    db_session.refresh(second_device)

    with pytest.raises(HTTPException) as exc:
        SelfOrderService.create(
            db=db_session,
            payload=_payload(
                data,
                self_order_uuid=order_uuid,
                device_code=second_device.device_code,
            ),
        )

    assert exc.value.status_code == 409


def test_device_must_belong_to_requested_branch(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    other = _seed(
        db_session,
        device_source='BAR_TABLET',
    )

    payload = _payload(data)
    payload.branch_code = other['branch'].code

    with pytest.raises(HTTPException) as exc:
        SelfOrderService.create(
            db=db_session,
            payload=payload,
        )

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    'mode',
    [
        'UNKNOWN',
        'INACTIVE',
    ],
)
def test_unknown_or_inactive_device_is_rejected(
    db_session,
    mode,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    device_code = data['device'].device_code

    if mode == 'UNKNOWN':
        device_code = f'UNKNOWN-{uuid4().hex[:8]}'
    else:
        data['device'].is_active = False
        db_session.commit()

    with pytest.raises(HTTPException) as exc:
        SelfOrderService.create(
            db=db_session,
            payload=_payload(
                data,
                device_code=device_code,
            ),
        )

    assert exc.value.status_code == 404


def test_shared_pricing_rules_are_enforced(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    group = PosModifierGroup(
        name=f'Required {uuid4().hex[:8]}',
        required=True,
        min_select=1,
        max_select=1,
        is_active=True,
    )

    db_session.add(group)
    db_session.flush()

    db_session.add(
        PosProductModifierGroup(
            product_id=data['product'].id,
            modifier_group_id=group.id,
            sort_order=0,
        )
    )

    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        SelfOrderService.create(
            db=db_session,
            payload=_payload(data),
        )

    assert exc.value.status_code == 400


def test_get_lazily_expires_overdue_draft(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    created = SelfOrderService.create(
        db=db_session,
        payload=_payload(data),
    )

    created.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )

    db_session.commit()

    recovered = SelfOrderService.get(
        db=db_session,
        self_order_uuid=created.self_order_uuid,
        device_code=data['device'].device_code,
    )

    assert recovered.status == 'EXPIRED'

    db_session.refresh(created)
    assert created.status == 'EXPIRED'


def test_cancel_only_allows_pre_payment_states(
    db_session,
):
    SelfOrderService = _service()
    data = _seed(db_session)

    first = SelfOrderService.create(
        db=db_session,
        payload=_payload(data),
    )

    cancelled = SelfOrderService.cancel(
        db=db_session,
        self_order_uuid=first.self_order_uuid,
        device_code=data['device'].device_code,
    )

    assert cancelled.status == 'CANCELLED'

    second = SelfOrderService.create(
        db=db_session,
        payload=_payload(data),
    )

    second.status = 'PAYMENT_PROCESSING'
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        SelfOrderService.cancel(
            db=db_session,
            self_order_uuid=second.self_order_uuid,
            device_code=data['device'].device_code,
        )

    assert exc.value.status_code == 409
