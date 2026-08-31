from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

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


def make_customer(
    db_session,
    *,
    name="Ana Cliente",
    phone="3221234567",
):
    customer = PosCustomerService.create(
        db_session,
        name=name,
        phone=phone,
        email="ana@example.com",
    )
    db_session.commit()
    db_session.refresh(customer)
    return customer


def seed_catalog(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Customer CRM Branch {suffix}",
        code=f"crm-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Coffee CRM {suffix}",
        slug=f"coffee-crm-{suffix}",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name="Americano CRM",
        base_price=Decimal("50.00"),
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
        )
    )

    db_session.flush()

    return branch, product


def make_order_payload(
    branch,
    product,
    *,
    customer_uuid,
    created_at=None,
):
    now = (
        created_at
        or datetime.now(timezone.utc)
    )

    return PosOrderCreate(
        order_uuid=uuid4(),
        customer_uuid=customer_uuid,
        branch_code=branch.code,
        terminal_id="CUSTOMER-CRM-TEST",
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


def test_pos_can_create_customer(
    client,
):
    response = client.post(
        "/pos/customers",
        json={
            "name": "María POS",
            "phone": "322 555 0101",
            "email": "maria@example.com",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "María POS"
    assert data["phone_normalized"] == "+523225550101"
    assert data["loyalty_points"] == 0
    assert data["visits"] == 0
    assert Decimal(str(data["total_spent"])) == Decimal("0")
    assert data["last_purchase_at"] is None


def test_pos_can_search_customer(
    client,
    db_session,
):
    customer = make_customer(
        db_session,
        name="Carlos Mendoza",
        phone="3225550202",
    )

    response = client.get(
        "/pos/customers",
        params={"q": "Carlos"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["customer_uuid"] == customer.customer_uuid
    assert data[0]["name"] == "Carlos Mendoza"


def test_pos_can_get_customer_summary_without_sales(
    client,
    db_session,
):
    customer = make_customer(
        db_session,
        name="Cliente Sin Ventas",
        phone="3225550303",
    )

    response = client.get(
        f"/pos/customers/{customer.customer_uuid}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_uuid"] == customer.customer_uuid
    assert data["loyalty_points"] == 0
    assert data["visits"] == 0
    assert Decimal(str(data["total_spent"])) == Decimal("0")
    assert data["last_purchase_at"] is None


def test_order_updates_customer_last_activity(
    db_session,
):
    branch, product = seed_catalog(db_session)

    customer = make_customer(
        db_session,
        name="Cliente Activo",
        phone="3225550404",
    )

    assert customer.last_activity_at is None

    PosOrderService.create(
        db_session,
        make_order_payload(
            branch,
            product,
            customer_uuid=customer.customer_uuid,
        ),
    )

    db_session.refresh(customer)

    assert customer.last_activity_at is not None


def test_admin_can_edit_customer(
    client,
    db_session,
    super_headers,
):
    customer = make_customer(
        db_session,
        name="Nombre Viejo",
        phone="3225550505",
    )

    response = client.patch(
        f"/admin/pos/customers/{customer.customer_uuid}",
        headers=super_headers,
        json={
            "name": "Nombre Nuevo",
            "phone": "3225550505",
            "email": "nuevo@example.com",
            "birthday": "1994-04-12",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Nombre Nuevo"
    assert data["email"] == "nuevo@example.com"
    assert data["birthday"] == "1994-04-12"


def test_admin_rejects_duplicate_customer_phone(
    client,
    db_session,
    super_headers,
):
    make_customer(
        db_session,
        name="Cliente Uno",
        phone="3225550606",
    )

    second = make_customer(
        db_session,
        name="Cliente Dos",
        phone="3225550707",
    )

    response = client.patch(
        f"/admin/pos/customers/{second.customer_uuid}",
        headers=super_headers,
        json={
            "name": "Cliente Dos",
            "phone": "3225550606",
        },
    )

    assert response.status_code == 409


def test_admin_can_adjust_loyalty_points(
    client,
    db_session,
    super_headers,
):
    customer = make_customer(
        db_session,
        name="Cliente Loyalty",
        phone="3225550808",
    )

    add_response = client.post(
        (
            f"/admin/pos/customers/"
            f"{customer.customer_uuid}/loyalty-adjustments"
        ),
        headers=super_headers,
        json={"points": 25},
    )

    assert add_response.status_code == 201

    subtract_response = client.post(
        (
            f"/admin/pos/customers/"
            f"{customer.customer_uuid}/loyalty-adjustments"
        ),
        headers=super_headers,
        json={"points": -5},
    )

    assert subtract_response.status_code == 201

    profile_response = client.get(
        f"/admin/pos/customers/{customer.customer_uuid}/profile",
        headers=super_headers,
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["loyalty_points"] == 20


def test_admin_rejects_zero_loyalty_adjustment(
    client,
    db_session,
    super_headers,
):
    customer = make_customer(
        db_session,
        name="Cliente Zero",
        phone="3225550909",
    )

    response = client.post(
        (
            f"/admin/pos/customers/"
            f"{customer.customer_uuid}/loyalty-adjustments"
        ),
        headers=super_headers,
        json={"points": 0},
    )

    assert response.status_code == 422



def test_customer_metrics_use_real_orders(
    client,
    db_session,
):
    branch, product = seed_catalog(
        db_session
    )

    customer = make_customer(
        db_session,
        name="Cliente Métricas",
        phone="3225551010",
    )

    first_at = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second_at = datetime(
        2026,
        8,
        3,
        14,
        30,
        tzinfo=timezone.utc,
    )

    cancelled_at = datetime(
        2026,
        8,
        5,
        16,
        0,
        tzinfo=timezone.utc,
    )

    first_payload = make_order_payload(
        branch,
        product,
        customer_uuid=customer.customer_uuid,
        created_at=first_at,
    )

    second_payload = make_order_payload(
        branch,
        product,
        customer_uuid=customer.customer_uuid,
        created_at=second_at,
    )

    cancelled_payload = make_order_payload(
        branch,
        product,
        customer_uuid=customer.customer_uuid,
        created_at=cancelled_at,
    )

    PosOrderService.create(
        db_session,
        first_payload,
    )

    PosOrderService.create(
        db_session,
        second_payload,
    )

    PosOrderService.create(
        db_session,
        cancelled_payload,
    )

    cancelled_order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(cancelled_payload.order_uuid)
        )
        .one()
    )

    cancelled_order.status = "CANCELLED"
    db_session.commit()

    response = client.get(
        f"/pos/customers/{customer.customer_uuid}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["visits"] == 2
    assert Decimal(
        str(data["total_spent"])
    ) == Decimal("100.00")

    assert data[
        "last_purchase_at"
    ].startswith(
        "2026-08-03T14:30"
    )


def test_admin_profile_contains_purchase_history(
    client,
    db_session,
    super_headers,
):
    branch, product = seed_catalog(
        db_session
    )

    customer = make_customer(
        db_session,
        name="Cliente Historial",
        phone="3225551111",
    )

    older = datetime(
        2026,
        8,
        2,
        9,
        15,
        tzinfo=timezone.utc,
    )

    newer = datetime(
        2026,
        8,
        6,
        17,
        45,
        tzinfo=timezone.utc,
    )

    PosOrderService.create(
        db_session,
        make_order_payload(
            branch,
            product,
            customer_uuid=customer.customer_uuid,
            created_at=older,
        ),
    )

    PosOrderService.create(
        db_session,
        make_order_payload(
            branch,
            product,
            customer_uuid=customer.customer_uuid,
            created_at=newer,
        ),
    )

    db_session.commit()

    response = client.get(
        (
            f"/admin/pos/customers/"
            f"{customer.customer_uuid}/profile"
        ),
        headers=super_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["visits"] == 2

    assert Decimal(
        str(data["total_spent"])
    ) == Decimal("100.00")

    assert len(data["orders"]) == 2

    latest = data["orders"][0]

    assert latest[
        "created_at_client"
    ].startswith(
        "2026-08-06T17:45"
    )

    assert latest["branch_code"] == branch.code
    assert latest["status"] == "NEW"

    assert Decimal(
        str(latest["total"])
    ) == Decimal("50.00")


def test_admin_customer_list_includes_metrics(
    client,
    db_session,
    super_headers,
):
    branch, product = seed_catalog(
        db_session
    )

    customer = make_customer(
        db_session,
        name="Cliente Lista CRM",
        phone="3225551212",
    )

    PosOrderService.create(
        db_session,
        make_order_payload(
            branch,
            product,
            customer_uuid=customer.customer_uuid,
        ),
    )

    db_session.commit()

    response = client.get(
        "/admin/pos/customers",
        params={
            "q": "Cliente Lista CRM",
        },
        headers=super_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0]["visits"] == 1

    assert Decimal(
        str(data[0]["total_spent"])
    ) == Decimal("50.00")

    assert (
        data[0]["last_purchase_at"]
        is not None
    )
