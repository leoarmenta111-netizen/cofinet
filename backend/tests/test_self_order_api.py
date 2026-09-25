from decimal import Decimal
from uuid import uuid4

from app.core.config import settings
from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_orders import PosOrder
from app.models.self_orders import (
    SelfOrderDevice,
    SelfOrderPaymentAttempt,
)


def _seed(
    db_session,
    *,
    source='KIOSK',
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f'Self API Branch {suffix}',
        code=f'self-api-{suffix}',
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

    return {
        'branch': branch,
        'product': product,
        'device': device,
    }


def _payload(data):
    return {
        'self_order_uuid': str(uuid4()),
        'branch_code': data['branch'].code,
        'device_code': data['device'].device_code,
        'items': [
            {
                'product_id': data['product'].id,
                'quantity': 2,
                'modifier_option_ids': [],
                'notes': 'Sin azúcar',
            }
        ],
    }


def _create(client, data):
    payload = _payload(data)

    response = client.post(
        '/self-orders',
        json=payload,
    )

    return payload, response


def test_create_self_order_returns_customer_contract(
    client,
    db_session,
):
    data = _seed(db_session)

    payload, response = _create(
        client,
        data,
    )

    assert response.status_code == 201

    body = response.json()

    assert (
        body['self_order_uuid']
        == payload['self_order_uuid']
    )

    assert (
        body['branch_code']
        == data['branch'].code
    )

    assert (
        body['device_code']
        == data['device'].device_code
    )

    assert body['source'] == 'KIOSK'
    assert body['status'] == 'AWAITING_PAYMENT'

    assert Decimal(
        str(body['subtotal'])
    ) == Decimal('114.00')

    assert Decimal(
        str(body['total'])
    ) == Decimal('114.00')

    assert body['currency'] == 'MXN'
    assert body['folio'] is None
    assert body['pos_order_uuid'] is None

    assert len(body['items']) == 1

    item = body['items'][0]

    assert (
        item['product_name']
        == data['product'].name
    )

    assert (
        item['preparation_station']
        == 'BAR'
    )

    assert item['quantity'] == 2

    assert Decimal(
        str(item['unit_price'])
    ) == Decimal('57.00')

    assert Decimal(
        str(item['line_total'])
    ) == Decimal('114.00')

    assert item['notes'] == 'Sin azúcar'
    assert item['modifiers'] == []


def test_get_self_order_requires_matching_device(
    client,
    db_session,
):
    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    response = client.get(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
        ),
        params={
            'device_code': (
                data['device'].device_code
            ),
        },
    )

    assert response.status_code == 200
    assert (
        response.json()['status']
        == 'AWAITING_PAYMENT'
    )

    wrong_device = client.get(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
        ),
        params={
            'device_code': 'OTHER-DEVICE',
        },
    )

    assert wrong_device.status_code == 404


def test_cancel_self_order_is_idempotent(
    client,
    db_session,
):
    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    url = (
        f"/self-orders/"
        f"{payload['self_order_uuid']}"
        f"/cancel"
    )

    request = {
        'device_code': (
            data['device'].device_code
        ),
    }

    first = client.post(
        url,
        json=request,
    )

    second = client.post(
        url,
        json=request,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        first.json()['status']
        == 'CANCELLED'
    )

    assert (
        second.json()['status']
        == 'CANCELLED'
    )


def test_approved_payment_returns_submitted_order(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'development',
        raising=False,
    )

    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    attempt_uuid = str(uuid4())

    response = client.post(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
            f"/payment-attempts"
        ),
        json={
            'device_code': (
                data['device'].device_code
            ),
            'payment_attempt_uuid': (
                attempt_uuid
            ),
            'simulated_outcome': (
                'APPROVED'
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body['status'] == 'SUBMITTED'
    assert body['folio'] is not None
    assert body['pos_order_uuid'] is not None

    orders = (
        db_session.query(PosOrder)
        .all()
    )

    assert len(orders) == 1

    assert orders[0].source == 'KIOSK'

    assert (
        orders[0].terminal_id
        == data['device'].device_code
    )


def test_declined_payment_does_not_create_pos_order(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'development',
        raising=False,
    )

    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    response = client.post(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
            f"/payment-attempts"
        ),
        json={
            'device_code': (
                data['device'].device_code
            ),
            'payment_attempt_uuid': (
                str(uuid4())
            ),
            'simulated_outcome': (
                'DECLINED'
            ),
        },
    )

    assert response.status_code == 200

    assert (
        response.json()['status']
        == 'PAYMENT_DECLINED'
    )

    assert (
        db_session.query(PosOrder).count()
        == 0
    )


def test_unknown_payment_surfaces_recovery_state(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'development',
        raising=False,
    )

    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    response = client.post(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
            f"/payment-attempts"
        ),
        json={
            'device_code': (
                data['device'].device_code
            ),
            'payment_attempt_uuid': (
                str(uuid4())
            ),
            'simulated_outcome': (
                'UNKNOWN'
            ),
        },
    )

    assert response.status_code == 200

    assert (
        response.json()['status']
        == 'PAYMENT_UNKNOWN'
    )

    assert (
        db_session.query(PosOrder).count()
        == 0
    )


def test_payment_attempt_http_retry_is_exactly_once(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'development',
        raising=False,
    )

    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    attempt_uuid = str(uuid4())

    url = (
        f"/self-orders/"
        f"{payload['self_order_uuid']}"
        f"/payment-attempts"
    )

    request = {
        'device_code': (
            data['device'].device_code
        ),
        'payment_attempt_uuid': (
            attempt_uuid
        ),
        'simulated_outcome': (
            'APPROVED'
        ),
    }

    first = client.post(
        url,
        json=request,
    )

    second = client.post(
        url,
        json=request,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        first.json()['pos_order_uuid']
        == second.json()['pos_order_uuid']
    )

    assert (
        db_session.query(PosOrder).count()
        == 1
    )

    assert (
        db_session.query(
            SelfOrderPaymentAttempt
        ).count()
        == 1
    )


def test_simulated_payment_is_blocked_in_production(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        'APP_ENV',
        'production',
        raising=False,
    )

    data = _seed(db_session)

    payload, created = _create(
        client,
        data,
    )

    assert created.status_code == 201

    response = client.post(
        (
            f"/self-orders/"
            f"{payload['self_order_uuid']}"
            f"/payment-attempts"
        ),
        json={
            'device_code': (
                data['device'].device_code
            ),
            'payment_attempt_uuid': (
                str(uuid4())
            ),
            'simulated_outcome': (
                'APPROVED'
            ),
        },
    )

    assert response.status_code == 403

    assert (
        db_session.query(PosOrder).count()
        == 0
    )

    assert (
        db_session.query(
            SelfOrderPaymentAttempt
        ).count()
        == 0
    )
