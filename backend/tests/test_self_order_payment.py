from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_orders import (
    PosOrder,
    PosOrderStation,
    PosPayment,
)
from app.models.self_orders import (
    SelfOrderDevice,
    SelfOrderPaymentAttempt,
)
from app.schemas.self_orders import SelfOrderCreate
from app.services.self_order_service import SelfOrderService


def _payment_types():
    from app.services.self_order_payment import (
        PaymentResult,
        SelfOrderPaymentService,
        SimulatedPaymentProvider,
    )

    return (
        PaymentResult,
        SelfOrderPaymentService,
        SimulatedPaymentProvider,
    )


def _seed(
    db_session,
    *,
    source='KIOSK',
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f'Payment Branch {suffix}',
        code=f'payment-{suffix}',
        is_active=True,
    )

    category = PosCategory(
        name=f'Coffee {suffix}',
        slug=f'coffee-{suffix}',
        is_active=True,
    )

    db_session.add_all([
        branch,
        category,
    ])
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
        source=source,
        is_active=True,
    )

    db_session.add_all([
        branch_product,
        device,
    ])

    db_session.commit()

    for row in (
        branch,
        product,
        branch_product,
        device,
    ):
        db_session.refresh(row)

    payload = SelfOrderCreate(
        self_order_uuid=uuid4(),
        branch_code=branch.code,
        device_code=device.device_code,
        items=[
            {
                'product_id': product.id,
                'quantity': 2,
                'modifier_option_ids': [],
                'notes': 'Sin azúcar',
            }
        ],
    )

    self_order = SelfOrderService.create(
        db=db_session,
        payload=payload,
    )

    return {
        'branch': branch,
        'product': product,
        'branch_product': branch_product,
        'device': device,
        'self_order': self_order,
    }


class RecordingProvider:
    provider_name = 'TEST'

    def __init__(
        self,
        result_type,
        outcome,
    ):
        self.result_type = result_type
        self.outcome = outcome
        self.calls = []

    def charge(
        self,
        *,
        payment_attempt_uuid,
        amount,
    ):
        self.calls.append({
            'payment_attempt_uuid': (
                str(payment_attempt_uuid)
            ),
            'amount': Decimal(amount),
        })

        return self.result_type(
            status=self.outcome,
            external_reference=(
                f'test-{payment_attempt_uuid}'
            ),
        )


def _recording_provider(outcome):
    PaymentResult, _, _ = (
        _payment_types()
    )

    return RecordingProvider(
        PaymentResult,
        outcome,
    )


def _process(
    db_session,
    data,
    *,
    outcome='APPROVED',
    attempt_uuid=None,
    provider=None,
):
    _, SelfOrderPaymentService, _ = (
        _payment_types()
    )

    provider = (
        provider
        or _recording_provider(outcome)
    )

    attempt_uuid = (
        attempt_uuid or uuid4()
    )

    result = SelfOrderPaymentService.process(
        db=db_session,
        self_order_uuid=(
            data['self_order'].self_order_uuid
        ),
        device_code=(
            data['device'].device_code
        ),
        payment_attempt_uuid=attempt_uuid,
        provider=provider,
    )

    return (
        result,
        provider,
        attempt_uuid,
    )


def test_approved_payment_materializes_one_pos_order(
    db_session,
):
    data = _seed(db_session)

    result, provider, attempt_uuid = (
        _process(
            db_session,
            data,
            outcome='APPROVED',
        )
    )

    assert result.status == 'SUBMITTED'
    assert len(provider.calls) == 1

    attempt = (
        db_session.query(
            SelfOrderPaymentAttempt
        )
        .filter(
            SelfOrderPaymentAttempt
            .payment_attempt_uuid
            == str(attempt_uuid)
        )
        .one()
    )

    assert attempt.status == 'APPROVED'

    assert Decimal(
        attempt.amount
    ) == Decimal('114.00')

    orders = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .all()
    )

    assert len(orders) == 1

    order = orders[0]

    assert order.source == 'KIOSK'

    assert (
        order.terminal_id
        == data['device'].device_code
    )

    assert order.payment_status == 'PAID'

    assert Decimal(
        order.subtotal
    ) == Decimal('114.00')

    assert Decimal(
        order.total
    ) == Decimal('114.00')

    assert len(order.items) == 1

    item = order.items[0]

    assert (
        item.product_name
        == data['product'].name
    )

    assert Decimal(
        item.unit_price
    ) == Decimal('57.00')

    assert item.quantity == 2
    assert item.notes == 'Sin azúcar'

    stations = (
        db_session.query(
            PosOrderStation
        )
        .filter(
            PosOrderStation.order_id
            == order.id
        )
        .all()
    )

    assert [
        row.station
        for row in stations
    ] == ['BAR']

    payment = (
        db_session.query(
            PosPayment
        )
        .filter(
            PosPayment.order_id
            == order.id
        )
        .one()
    )

    assert payment.method == 'CARD_EXTERNAL'

    assert Decimal(
        payment.amount
    ) == Decimal('114.00')

    assert (
        payment.payment_uuid
        == str(attempt_uuid)
    )


@pytest.mark.parametrize(
    (
        'outcome',
        'expected_status',
    ),
    [
        (
            'DECLINED',
            'PAYMENT_DECLINED',
        ),
        (
            'UNKNOWN',
            'PAYMENT_UNKNOWN',
        ),
    ],
)
def test_nonapproved_payment_never_reaches_pos_or_kds(
    db_session,
    outcome,
    expected_status,
):
    data = _seed(db_session)

    result, _, attempt_uuid = (
        _process(
            db_session,
            data,
            outcome=outcome,
        )
    )

    assert result.status == expected_status

    attempt = (
        db_session.query(
            SelfOrderPaymentAttempt
        )
        .filter(
            SelfOrderPaymentAttempt
            .payment_attempt_uuid
            == str(attempt_uuid)
        )
        .one()
    )

    assert attempt.status == outcome

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .count()
        == 0
    )

    assert (
        db_session.query(
            PosOrderStation
        )
        .count()
        == 0
    )


def test_same_approved_attempt_is_exactly_once(
    db_session,
):
    data = _seed(db_session)

    (
        PaymentResult,
        SelfOrderPaymentService,
        _,
    ) = _payment_types()

    attempt_uuid = uuid4()

    provider = RecordingProvider(
        PaymentResult,
        'APPROVED',
    )

    first = (
        SelfOrderPaymentService.process(
            db=db_session,
            self_order_uuid=(
                data['self_order']
                .self_order_uuid
            ),
            device_code=(
                data['device'].device_code
            ),
            payment_attempt_uuid=(
                attempt_uuid
            ),
            provider=provider,
        )
    )

    second = (
        SelfOrderPaymentService.process(
            db=db_session,
            self_order_uuid=(
                data['self_order']
                .self_order_uuid
            ),
            device_code=(
                data['device'].device_code
            ),
            payment_attempt_uuid=(
                attempt_uuid
            ),
            provider=provider,
        )
    )

    assert first.id == second.id
    assert first.status == 'SUBMITTED'
    assert second.status == 'SUBMITTED'

    assert len(provider.calls) == 1

    assert (
        db_session.query(
            SelfOrderPaymentAttempt
        )
        .filter(
            SelfOrderPaymentAttempt
            .payment_attempt_uuid
            == str(attempt_uuid)
        )
        .count()
        == 1
    )

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .count()
        == 1
    )


def test_unknown_blocks_a_new_payment_attempt(
    db_session,
):
    data = _seed(db_session)

    first, _, _ = _process(
        db_session,
        data,
        outcome='UNKNOWN',
    )

    assert first.status == 'PAYMENT_UNKNOWN'

    provider = _recording_provider(
        'APPROVED'
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        _process(
            db_session,
            data,
            attempt_uuid=uuid4(),
            provider=provider,
        )

    assert exc.value.status_code == 409
    assert provider.calls == []

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .count()
        == 0
    )


def test_declined_can_retry_with_new_attempt(
    db_session,
):
    data = _seed(db_session)

    declined, _, _ = _process(
        db_session,
        data,
        outcome='DECLINED',
    )

    assert (
        declined.status
        == 'PAYMENT_DECLINED'
    )

    approved, _, _ = _process(
        db_session,
        data,
        outcome='APPROVED',
        attempt_uuid=uuid4(),
    )

    assert approved.status == 'SUBMITTED'

    assert (
        db_session.query(
            SelfOrderPaymentAttempt
        )
        .filter(
            SelfOrderPaymentAttempt
            .self_order_id
            == data['self_order'].id
        )
        .count()
        == 2
    )

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .count()
        == 1
    )


def test_materialization_uses_frozen_self_order_snapshot(
    db_session,
):
    data = _seed(db_session)

    frozen_name = (
        data['self_order']
        .items[0]
        .product_name
    )

    data[
        'branch_product'
    ].price = Decimal('199.00')

    data['product'].name = (
        'Changed after staging'
    )

    data['product'].is_active = False

    db_session.commit()

    result, _, _ = _process(
        db_session,
        data,
        outcome='APPROVED',
    )

    assert result.status == 'SUBMITTED'

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .one()
    )

    assert Decimal(
        order.total
    ) == Decimal('114.00')

    assert (
        order.items[0].product_name
        == frozen_name
    )

    assert Decimal(
        order.items[0].unit_price
    ) == Decimal('57.00')


def test_bar_tablet_source_is_preserved(
    db_session,
):
    data = _seed(
        db_session,
        source='BAR_TABLET',
    )

    result, _, _ = _process(
        db_session,
        data,
        outcome='APPROVED',
    )

    assert result.status == 'SUBMITTED'

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.self_order_id
            == data['self_order'].id
        )
        .one()
    )

    assert (
        order.source
        == 'BAR_TABLET'
    )


def test_simulated_provider_is_dev_qa_only(
    db_session,
    monkeypatch,
):
    (
        _,
        SelfOrderPaymentService,
        SimulatedPaymentProvider,
    ) = _payment_types()

    data = _seed(db_session)

    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'production',
        raising=False,
    )

    provider = (
        SimulatedPaymentProvider(
            outcome='APPROVED'
        )
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        SelfOrderPaymentService.process(
            db=db_session,
            self_order_uuid=(
                data['self_order']
                .self_order_uuid
            ),
            device_code=(
                data['device']
                .device_code
            ),
            payment_attempt_uuid=uuid4(),
            provider=provider,
        )

    assert exc.value.status_code == 403

    assert (
        db_session.query(
            SelfOrderPaymentAttempt
        )
        .filter(
            SelfOrderPaymentAttempt
            .self_order_id
            == data['self_order'].id
        )
        .count()
        == 0
    )

    db_session.refresh(
        data['self_order']
    )

    assert (
        data['self_order'].status
        == 'AWAITING_PAYMENT'
    )
