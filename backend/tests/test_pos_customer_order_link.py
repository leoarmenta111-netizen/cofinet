from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_customers import Customer
from app.models.pos_orders import PosOrder
from app.schemas.pos_orders import PosOrderCreate
from app.services.pos_customer_service import PosCustomerService
from app.services.pos_order_service import PosOrderService


def seed_catalog(db):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Test Branch {suffix}",
        code=f"test-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Coffee {suffix}",
        slug=f"coffee-{suffix}",
        is_active=True,
    )

    db.add_all([branch, category])
    db.flush()

    product = PosProduct(
        category_id=category.id,
        name="Americano",
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


def order_payload(
    branch,
    product,
    *,
    customer_uuid=None,
    order_uuid=None,
):
    now = datetime.now(timezone.utc)

    return PosOrderCreate(
        order_uuid=order_uuid or uuid4(),
        customer_uuid=customer_uuid,
        branch_code=branch.code,
        terminal_id="TEST-01",
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


def test_order_schema_preserves_customer_uuid(
    db_session,
):
    branch, product = seed_catalog(db_session)
    customer_uuid = uuid4()

    payload = order_payload(
        branch,
        product,
        customer_uuid=customer_uuid,
    )

    assert payload.customer_uuid == customer_uuid


def test_order_can_be_linked_to_customer(
    db_session,
):
    branch, product = seed_catalog(db_session)

    customer = PosCustomerService.create(
        db_session,
        name="María López",
        phone="322 123 4567",
    )

    db_session.commit()

    result = PosOrderService.create(
        db_session,
        order_payload(
            branch,
            product,
            customer_uuid=customer.customer_uuid,
        ),
    )

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == result.order_uuid
        )
        .one()
    )

    assert order.customer_id == customer.id
    assert result.customer_uuid == customer.customer_uuid


def test_order_retry_keeps_original_customer(
    db_session,
):
    branch, product = seed_catalog(db_session)

    first_customer = PosCustomerService.create(
        db_session,
        name="Cliente Uno",
        phone="3221112233",
    )

    second_customer = PosCustomerService.create(
        db_session,
        name="Cliente Dos",
        phone="3224445566",
    )

    db_session.commit()

    order_uuid = uuid4()

    first = PosOrderService.create(
        db_session,
        order_payload(
            branch,
            product,
            order_uuid=order_uuid,
            customer_uuid=first_customer.customer_uuid,
        ),
    )

    retry = PosOrderService.create(
        db_session,
        order_payload(
            branch,
            product,
            order_uuid=order_uuid,
            customer_uuid=second_customer.customer_uuid,
        ),
    )

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(order_uuid)
        )
        .one()
    )

    assert first.customer_uuid == first_customer.customer_uuid
    assert retry.customer_uuid == first_customer.customer_uuid
    assert order.customer_id == first_customer.id


def test_unknown_customer_is_rejected(
    db_session,
):
    branch, product = seed_catalog(db_session)

    try:
        PosOrderService.create(
            db_session,
            order_payload(
                branch,
                product,
                customer_uuid=uuid4(),
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Customer not found"
    else:
        raise AssertionError(
            "Unknown customer should be rejected"
        )
