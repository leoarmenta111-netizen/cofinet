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


def seed_station_catalog(
    db_session,
    *,
    branch_code,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Station API {suffix}",
        code=branch_code,
        is_active=True,
    )

    category = PosCategory(
        name=f"Station API Products {suffix}",
        slug=f"station-api-products-{suffix}",
        is_active=True,
    )

    db_session.add_all([
        branch,
        category,
    ])
    db_session.flush()

    products = {}

    for name, station in (
        ("Club Sandwich", "KITCHEN"),
        ("Latte", "BAR"),
        ("Agua Embotellada", "NONE"),
    ):
        product = PosProduct(
            category_id=category.id,
            name=f"{name} {suffix}",
            base_price=Decimal("50.00"),
            preparation_station=station,
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

        products[station] = product

    db_session.flush()

    return branch, products


def create_order(
    db_session,
    branch,
    products,
    stations,
):
    now = datetime.now(timezone.utc)

    payload = PosOrderCreate(
        order_uuid=uuid4(),
        branch_code=branch.code,
        terminal_id="STATION-API-01",
        created_at_client=now,
        items=[
            {
                "product_id": products[station].id,
                "quantity": 1,
                "notes": (
                    f"Nota {station}"
                ),
            }
            for station in stations
        ],
        payment={
            "payment_uuid": uuid4(),
            "method": "CASH",
            "amount_tendered": "1000.00",
            "created_at_client": now,
        },
    )

    return PosOrderService.create(
        db_session,
        payload,
    )


def get_order_model(
    db_session,
    order_uuid,
):
    return (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == order_uuid
        )
        .one()
    )


def test_kitchen_feed_returns_only_kitchen_items(
    client,
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        branch_code="station-api-kitchen",
    )

    order = create_order(
        db_session,
        branch,
        products,
        [
            "KITCHEN",
            "BAR",
            "NONE",
        ],
    )

    response = client.get(
        "/pos/orders/stations/KITCHEN",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["station"] == "KITCHEN"
    assert data["count"] == 1

    returned = data["orders"][0]

    assert (
        returned["order_uuid"]
        == order.order_uuid
    )

    assert returned["station_status"] == "NEW"

    assert [
        item["preparation_station"]
        for item in returned["items"]
    ] == ["KITCHEN"]

    assert (
        returned["items"][0]["notes"]
        == "Nota KITCHEN"
    )


def test_bar_feed_returns_only_bar_items(
    client,
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        branch_code="station-api-bar",
    )

    order = create_order(
        db_session,
        branch,
        products,
        [
            "KITCHEN",
            "BAR",
            "NONE",
        ],
    )

    response = client.get(
        "/pos/orders/stations/BAR",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["station"] == "BAR"
    assert data["count"] == 1

    returned = data["orders"][0]

    assert (
        returned["order_uuid"]
        == order.order_uuid
    )

    assert [
        item["preparation_station"]
        for item in returned["items"]
    ] == ["BAR"]


def test_station_feed_is_strictly_branch_scoped(
    client,
    db_session,
):
    branch_a, products_a = seed_station_catalog(
        db_session,
        branch_code="station-api-a",
    )

    branch_b, products_b = seed_station_catalog(
        db_session,
        branch_code="station-api-b",
    )

    order_a = create_order(
        db_session,
        branch_a,
        products_a,
        ["KITCHEN"],
    )

    create_order(
        db_session,
        branch_b,
        products_b,
        ["KITCHEN"],
    )

    response = client.get(
        "/pos/orders/stations/KITCHEN",
        params={
            "branch_code": branch_a.code,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1

    assert (
        data["orders"][0]["order_uuid"]
        == order_a.order_uuid
    )


def test_station_status_progression_recalculates_order(
    client,
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        branch_code="station-api-progress",
    )

    order = create_order(
        db_session,
        branch,
        products,
        [
            "KITCHEN",
            "BAR",
        ],
    )

    response = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PREPARING"

    stored = get_order_model(
        db_session,
        order.order_uuid,
    )

    assert stored.status == "PREPARING"

    response = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch.code,
            "status": "READY",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"

    stored = get_order_model(
        db_session,
        order.order_uuid,
    )

    # Kitchen is still NEW, so whole order
    # cannot be READY yet.
    assert stored.status == "PREPARING"

    response = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/KITCHEN"
        ),
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert response.status_code == 200

    response = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/KITCHEN"
        ),
        json={
            "branch_code": branch.code,
            "status": "READY",
        },
    )

    assert response.status_code == 200

    stored = get_order_model(
        db_session,
        order.order_uuid,
    )

    assert stored.status == "READY"


def test_station_status_same_value_is_idempotent(
    client,
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        branch_code="station-api-idempotent",
    )

    order = create_order(
        db_session,
        branch,
        products,
        ["BAR"],
    )

    first = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert first.status_code == 200

    second = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert second.status_code == 200
    assert second.json()["status"] == "PREPARING"


def test_station_status_rejects_backward_transition(
    client,
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        branch_code="station-api-backward",
    )

    order = create_order(
        db_session,
        branch,
        products,
        ["KITCHEN"],
    )

    for station_status in (
        "PREPARING",
        "READY",
    ):
        response = client.patch(
            (
                f"/pos/orders/{order.order_uuid}"
                "/stations/KITCHEN"
            ),
            json={
                "branch_code": branch.code,
                "status": station_status,
            },
        )

        assert response.status_code == 200

    response = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/KITCHEN"
        ),
        json={
            "branch_code": branch.code,
            "status": "PREPARING",
        },
    )

    assert response.status_code == 409


def test_station_update_is_branch_scoped(
    client,
    db_session,
):
    branch_a, products_a = seed_station_catalog(
        db_session,
        branch_code="station-update-a",
    )

    branch_b, _ = seed_station_catalog(
        db_session,
        branch_code="station-update-b",
    )

    order = create_order(
        db_session,
        branch_a,
        products_a,
        ["BAR"],
    )

    same_branch = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch_a.code,
            "status": "PREPARING",
        },
    )

    assert same_branch.status_code == 200

    wrong_branch = client.patch(
        (
            f"/pos/orders/{order.order_uuid}"
            "/stations/BAR"
        ),
        json={
            "branch_code": branch_b.code,
            "status": "READY",
        },
    )

    assert wrong_branch.status_code == 404
