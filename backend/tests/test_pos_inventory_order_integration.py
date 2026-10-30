from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)
from app.models.pos_orders import (
    PosOrder,
    PosOrderItem,
    PosPayment,
)
from app.services.pos_inventory_service import PosInventoryService


def _seed_product(db_session, *, label="Inventory Sale"):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"{label} Branch {suffix}",
        code=f"inv-sale-{suffix}",
        is_active=True,
    )
    category = PosCategory(
        name=f"{label} Category {suffix}",
        slug=f"inv-sale-{suffix}",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"{label} Product {suffix}",
        sku=f"INV-{suffix}",
        base_price=Decimal("50.00"),
        preparation_station="BAR",
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()

    db_session.add(
        PosBranchProduct(
            branch_id=branch.id,
            product_id=product.id,
            price=None,
            is_available=True,
            sort_order=0,
        )
    )
    db_session.commit()

    return branch, product


def _track(
    db_session,
    *,
    branch,
    product,
    initial,
    threshold="1.000",
):
    balance = PosInventoryService.configure_tracking(
        db_session,
        branch=branch,
        product=product,
        is_tracked=True,
        initial_quantity=Decimal(initial),
        low_stock_threshold=Decimal(threshold),
    )
    db_session.commit()
    db_session.refresh(balance)
    return balance


def _payload(
    branch,
    product,
    *,
    quantity=1,
    order_uuid=None,
    payment_uuid=None,
):
    now = datetime.now(timezone.utc)

    return {
        "order_uuid": str(order_uuid or uuid4()),
        "branch_code": branch.code,
        "terminal_id": "INVENTORY-TEST-01",
        "created_at_client": now.isoformat(),
        "items": [
            {
                "product_id": product.id,
                "quantity": quantity,
            }
        ],
        "payment": {
            "payment_uuid": str(payment_uuid or uuid4()),
            "method": "CASH",
            "amount_tendered": "500.00",
            "created_at_client": now.isoformat(),
        },
    }


def _balance(db_session, branch, product):
    db_session.expire_all()

    item = (
        db_session.query(PosInventoryItem)
        .filter(
            PosInventoryItem.product_id == product.id
        )
        .one()
    )

    return (
        db_session.query(PosInventoryBalance)
        .filter(
            PosInventoryBalance.branch_id == branch.id,
            PosInventoryBalance.inventory_item_id == item.id,
        )
        .one()
    )


def _sale_movements(db_session, order_id=None):
    query = db_session.query(PosInventoryMovement).filter(
        PosInventoryMovement.movement_type == "SALE"
    )

    if order_id is not None:
        query = query.filter(
            PosInventoryMovement.order_id == order_id
        )

    return query.order_by(
        PosInventoryMovement.id
    ).all()


def test_online_paid_sale_deducts_inventory_once(
    client,
    db_session,
):
    branch, product = _seed_product(db_session)

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="3.000",
    )

    payload = _payload(
        branch,
        product,
        quantity=2,
    )

    response = client.post(
        "/pos/orders",
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["payment_status"] == "PAID"

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .one()
    )
    order_item = (
        db_session.query(PosOrderItem)
        .filter(
            PosOrderItem.order_id == order.id
        )
        .one()
    )

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("1.000")
    )

    movements = _sale_movements(
        db_session,
        order.id,
    )

    assert len(movements) == 1
    assert movements[0].order_id == order.id
    assert movements[0].order_item_id == order_item.id
    assert (
        Decimal(movements[0].quantity_delta)
        == Decimal("-2.000")
    )


def test_online_insufficient_stock_rolls_back_entire_sale(
    client,
    db_session,
):
    branch, product = _seed_product(db_session)

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="1.000",
    )

    payload = _payload(
        branch,
        product,
        quantity=2,
    )

    response = client.post(
        "/pos/orders",
        json=payload,
    )

    assert response.status_code == 409

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .count()
        == 0
    )

    assert (
        db_session.query(PosPayment)
        .filter(
            PosPayment.payment_uuid
            == payload["payment"]["payment_uuid"]
        )
        .count()
        == 0
    )

    assert _sale_movements(db_session) == []

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("1.000")
    )


def test_online_retry_same_order_uuid_deducts_only_once(
    client,
    db_session,
):
    branch, product = _seed_product(db_session)

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="3.000",
    )

    order_uuid = uuid4()
    payment_uuid = uuid4()

    payload = _payload(
        branch,
        product,
        quantity=2,
        order_uuid=order_uuid,
        payment_uuid=payment_uuid,
    )

    first = client.post(
        "/pos/orders",
        json=payload,
    )
    second = client.post(
        "/pos/orders",
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert (
        first.json()["order_uuid"]
        == second.json()["order_uuid"]
        == str(order_uuid)
    )

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == str(order_uuid)
        )
        .count()
        == 1
    )

    assert (
        db_session.query(PosPayment)
        .filter(
            PosPayment.payment_uuid == str(payment_uuid)
        )
        .count()
        == 1
    )

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == str(order_uuid)
        )
        .one()
    )

    assert len(
        _sale_movements(
            db_session,
            order.id,
        )
    ) == 1

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("1.000")
    )


def test_offline_sync_can_replay_sale_into_negative_stock_once(
    client,
    db_session,
):
    branch, product = _seed_product(
        db_session,
        label="Offline",
    )

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="0.000",
    )

    payload = _payload(
        branch,
        product,
        quantity=1,
    )

    first = client.post(
        "/pos/orders/sync",
        json=payload,
    )

    assert first.status_code == 201
    assert first.json()["payment_status"] == "PAID"

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .one()
    )

    assert (
        db_session.query(PosPayment)
        .filter(
            PosPayment.order_id == order.id
        )
        .count()
        == 1
    )

    balance = _balance(
        db_session,
        branch,
        product,
    )

    assert (
        Decimal(balance.quantity_on_hand)
        == Decimal("-1.000")
    )

    assert (
        PosInventoryService.status_for(
            tracked=balance.is_tracked,
            quantity_on_hand=balance.quantity_on_hand,
            threshold=balance.low_stock_threshold,
        )
        == "REVIEW"
    )

    assert len(
        _sale_movements(
            db_session,
            order.id,
        )
    ) == 1

    second = client.post(
        "/pos/orders/sync",
        json=payload,
    )

    assert second.status_code == 201

    assert (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .count()
        == 1
    )

    assert (
        db_session.query(PosPayment)
        .filter(
            PosPayment.order_id == order.id
        )
        .count()
        == 1
    )

    assert len(
        _sale_movements(
            db_session,
            order.id,
        )
    ) == 1

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("-1.000")
    )


def test_untracked_product_still_completes_without_inventory_movement(
    client,
    db_session,
):
    branch, product = _seed_product(
        db_session,
        label="Untracked",
    )

    payload = _payload(
        branch,
        product,
        quantity=1,
    )

    response = client.post(
        "/pos/orders",
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["payment_status"] == "PAID"

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .one()
    )

    assert (
        _sale_movements(
            db_session,
            order.id,
        )
        == []
    )

    assert (
        db_session.query(PosInventoryBalance)
        .filter(
            PosInventoryBalance.branch_id
            == branch.id
        )
        .count()
        == 0
    )


def test_admin_full_refund_reverses_inventory_exactly_once(
    client,
    db_session,
    super_headers,
):
    branch, product = _seed_product(
        db_session,
        label="Refund",
    )

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="5.000",
    )

    payload = _payload(
        branch,
        product,
        quantity=2,
    )

    sale = client.post(
        "/pos/orders",
        json=payload,
    )

    assert sale.status_code == 201

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == payload["order_uuid"]
        )
        .one()
    )

    order_item = (
        db_session.query(PosOrderItem)
        .filter(
            PosOrderItem.order_id == order.id
        )
        .one()
    )

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("3.000")
    )

    reason = "Customer requested full refund"

    first = client.post(
        (
            f"/admin/pos/sales/"
            f"{payload['order_uuid']}/refund"
        ),
        headers=super_headers,
        json={"reason": reason},
    )

    assert first.status_code == 200
    assert first.json()["payment_status"] == "REFUNDED"
    assert first.json()["status"] == "CANCELLED"

    db_session.expire_all()

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.id == order.id
        )
        .one()
    )

    assert stored.payment_status == "REFUNDED"
    assert stored.status == "CANCELLED"

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("5.000")
    )

    reversals = (
        db_session.query(PosInventoryMovement)
        .filter(
            PosInventoryMovement.order_id == order.id,
            PosInventoryMovement.movement_type
            == "SALE_REVERSAL",
        )
        .all()
    )

    assert len(reversals) == 1
    assert reversals[0].order_item_id == order_item.id
    assert reversals[0].note == reason
    assert reversals[0].created_by_admin_id is not None
    assert (
        Decimal(reversals[0].quantity_delta)
        == Decimal("2.000")
    )

    second = client.post(
        (
            f"/admin/pos/sales/"
            f"{payload['order_uuid']}/refund"
        ),
        headers=super_headers,
        json={"reason": reason},
    )

    assert second.status_code == 200
    assert second.json()["payment_status"] == "REFUNDED"

    assert (
        Decimal(
            _balance(
                db_session,
                branch,
                product,
            ).quantity_on_hand
        )
        == Decimal("5.000")
    )

    assert (
        db_session.query(PosInventoryMovement)
        .filter(
            PosInventoryMovement.order_id == order.id,
            PosInventoryMovement.movement_type
            == "SALE_REVERSAL",
        )
        .count()
        == 1
    )
