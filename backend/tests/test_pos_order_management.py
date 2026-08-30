from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_orders import PosOrder
from app.schemas.pos_orders import PosOrderCreate
from app.services.pos_order_service import PosOrderService


def seed_catalog(db):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Orders Branch {suffix}",
        code=f"orders-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Orders Coffee {suffix}",
        slug=f"orders-coffee-{suffix}",
        is_active=True,
    )

    db.add_all([branch, category])
    db.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Americano {suffix}",
        base_price=Decimal("50.00"),
        is_active=True,
    )

    db.add(product)
    db.flush()

    db.add(
        PosBranchProduct(
            branch_id=branch.id,
            product_id=product.id,
            price=None,
            is_available=True,
        )
    )

    db.flush()

    return branch, product


def order_payload(branch, product):
    now = datetime.now(timezone.utc)

    return PosOrderCreate(
        order_uuid=uuid4(),
        branch_code=branch.code,
        terminal_id="ORDERS-TEST-01",
        created_at_client=now,
        items=[
            {
                "product_id": product.id,
                "quantity": 1,
            }
        ],
        payment={
            "payment_uuid": uuid4(),
            "method": "CASH",
            "amount_tendered": "100.00",
            "created_at_client": now,
        },
    )


def create_order(db, branch, product):
    return PosOrderService.create(
        db,
        order_payload(branch, product),
    )


def test_list_orders_is_scoped_to_branch(
    client,
    db_session,
):
    branch_a, product_a = seed_catalog(db_session)
    branch_b, product_b = seed_catalog(db_session)

    order_a1 = create_order(
        db_session,
        branch_a,
        product_a,
    )
    order_a2 = create_order(
        db_session,
        branch_a,
        product_a,
    )

    create_order(
        db_session,
        branch_b,
        product_b,
    )

    response = client.get(
        "/pos/orders",
        params={
            "branch_code": branch_a.code,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 2

    returned = {
        item["order_uuid"]
        for item in body["orders"]
    }

    assert returned == {
        order_a1.order_uuid,
        order_a2.order_uuid,
    }


def test_get_order_is_scoped_to_branch(
    client,
    db_session,
):
    branch_a, product_a = seed_catalog(db_session)
    branch_b, _ = seed_catalog(db_session)

    order = create_order(
        db_session,
        branch_a,
        product_a,
    )

    response = client.get(
        f"/pos/orders/{order.order_uuid}",
        params={
            "branch_code": branch_a.code,
        },
    )

    assert response.status_code == 200
    assert response.json()["order_uuid"] == order.order_uuid

    wrong_branch = client.get(
        f"/pos/orders/{order.order_uuid}",
        params={
            "branch_code": branch_b.code,
        },
    )

    assert wrong_branch.status_code == 404
    assert wrong_branch.json()["detail"] == "Order not found"


def test_order_status_progression(
    client,
    db_session,
):
    branch, product = seed_catalog(db_session)

    order = create_order(
        db_session,
        branch,
        product,
    )

    for expected_status in (
        "PREPARING",
        "READY",
        "DELIVERED",
    ):
        response = client.patch(
            f"/pos/orders/{order.order_uuid}/status",
            json={
                "branch_code": branch.code,
                "status": expected_status,
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == expected_status

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == order.order_uuid
        )
        .one()
    )

    assert stored.status == "DELIVERED"


def test_invalid_order_status_transition_is_rejected(
    client,
    db_session,
):
    branch, product = seed_catalog(db_session)

    order = create_order(
        db_session,
        branch,
        product,
    )

    response = client.patch(
        f"/pos/orders/{order.order_uuid}/status",
        json={
            "branch_code": branch.code,
            "status": "READY",
        },
    )

    assert response.status_code == 409

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == order.order_uuid
        )
        .one()
    )

    assert stored.status == "NEW"


def test_list_orders_can_filter_by_status(
    client,
    db_session,
):
    branch, product = seed_catalog(db_session)

    preparing = create_order(
        db_session,
        branch,
        product,
    )

    new_order = create_order(
        db_session,
        branch,
        product,
    )

    response = client.patch(
        f"/pos/orders/{preparing.order_uuid}/status",
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert response.status_code == 200

    response = client.get(
        "/pos/orders",
        params={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert body["orders"][0]["order_uuid"] == preparing.order_uuid
    assert body["orders"][0]["status"] == "PREPARING"
    assert body["orders"][0]["order_uuid"] != new_order.order_uuid
