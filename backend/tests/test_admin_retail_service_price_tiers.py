from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailServicePriceTier,
)


def _branch(
    db_session,
    label,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"{label} {suffix}",
        code=f"{label.lower()}-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)

    return branch


def _service(
    client,
    headers,
    *,
    branch,
    sku,
):
    response = client.post(
        "/admin/retail/catalog/items",
        headers=headers,
        json={
            "branch_id": branch.id,
            "item_type": "SERVICE",
            "sku": sku,
            "name": f"Service {sku}",
            "description": None,
            "category": "Services",
            "base_unit_code": "PAGE",
            "cost": "0.00",
            "inventory_tracked": False,
            "low_stock_threshold": None,
            "max_stock": None,
            "is_active": True,
        },
    )

    assert response.status_code == 200

    return response.json()


def _product(
    client,
    headers,
    *,
    branch,
    sku,
):
    response = client.post(
        "/admin/retail/catalog/items",
        headers=headers,
        json={
            "branch_id": branch.id,
            "item_type": "PRODUCT",
            "sku": sku,
            "name": f"Product {sku}",
            "description": None,
            "category": "Products",
            "base_unit_code": "PIECE",
            "cost": "1.00",
            "inventory_tracked": False,
            "low_stock_threshold": None,
            "max_stock": None,
            "is_active": True,
        },
    )

    assert response.status_code == 200

    return response.json()


def _create_tier(
    client,
    headers,
    *,
    item_id,
    minimum,
    maximum,
    price,
):
    return client.post(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}/service-price-tiers"
        ),
        headers=headers,
        json={
            "min_quantity": minimum,
            "max_quantity": maximum,
            "unit_price": price,
        },
    )


def test_admin_retail_service_can_create_price_tier(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierCreate",
    )

    service = _service(
        client,
        super_headers,
        branch=branch,
        sku="COPY-001",
    )

    response = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="1.000",
        maximum="9.999",
        price="2.00",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["item_id"] == service["id"]

    assert (
        Decimal(str(data["unit_price"]))
        == Decimal("2.00")
    )


def test_admin_retail_product_rejects_service_price_tier(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierProduct",
    )

    product = _product(
        client,
        super_headers,
        branch=branch,
        sku="PRODUCT-001",
    )

    response = _create_tier(
        client,
        super_headers,
        item_id=product["id"],
        minimum="1.000",
        maximum=None,
        price="5.00",
    )

    assert response.status_code == 422


def test_admin_retail_service_price_tiers_cannot_overlap(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierOverlap",
    )

    service = _service(
        client,
        super_headers,
        branch=branch,
        sku="PRINT-001",
    )

    first = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="1.000",
        maximum="10.000",
        price="3.00",
    )

    assert first.status_code == 200

    overlap = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="10.000",
        maximum="20.000",
        price="2.50",
    )

    assert overlap.status_code == 409

    valid = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="10.001",
        maximum="20.000",
        price="2.50",
    )

    assert valid.status_code == 200


def test_admin_retail_service_price_tier_can_be_updated(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierUpdate",
    )

    service = _service(
        client,
        super_headers,
        branch=branch,
        sku="LAMINATE-001",
    )

    created = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="1.000",
        maximum="5.000",
        price="10.00",
    )

    assert created.status_code == 200

    tier_id = created.json()["id"]

    updated = client.patch(
        (
            "/admin/retail/catalog/"
            "service-price-tiers/"
            f"{tier_id}"
        ),
        headers=super_headers,
        json={
            "min_quantity": "2.000",
            "max_quantity": "8.000",
            "unit_price": "8.50",
        },
    )

    assert updated.status_code == 200

    data = updated.json()

    assert (
        Decimal(str(data["min_quantity"]))
        == Decimal("2.000")
    )

    assert (
        Decimal(str(data["max_quantity"]))
        == Decimal("8.000")
    )

    assert (
        Decimal(str(data["unit_price"]))
        == Decimal("8.50")
    )


def test_admin_retail_service_price_tier_update_cannot_overlap(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierUpdateOverlap",
    )

    service = _service(
        client,
        super_headers,
        branch=branch,
        sku="BIND-001",
    )

    first = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="1.000",
        maximum="10.000",
        price="5.00",
    )

    second = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="11.000",
        maximum="20.000",
        price="4.00",
    )

    assert first.status_code == 200
    assert second.status_code == 200

    response = client.patch(
        (
            "/admin/retail/catalog/"
            "service-price-tiers/"
            f"{second.json()['id']}"
        ),
        headers=super_headers,
        json={
            "min_quantity": "10.000",
        },
    )

    assert response.status_code == 409


def test_admin_retail_service_price_tier_can_be_deleted(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "TierDelete",
    )

    service = _service(
        client,
        super_headers,
        branch=branch,
        sku="SCAN-001",
    )

    created = _create_tier(
        client,
        super_headers,
        item_id=service["id"],
        minimum="1.000",
        maximum=None,
        price="4.00",
    )

    assert created.status_code == 200

    tier_id = created.json()["id"]

    deleted = client.delete(
        (
            "/admin/retail/catalog/"
            "service-price-tiers/"
            f"{tier_id}"
        ),
        headers=super_headers,
    )

    assert deleted.status_code == 200

    assert deleted.json() == {
        "deleted": True,
    }

    tier = db_session.execute(
        select(
            RetailServicePriceTier
        ).where(
            RetailServicePriceTier.id
            == tier_id
        )
    ).scalar_one_or_none()

    assert tier is None


def test_admin_retail_service_price_tier_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected = {
        (
            "/admin/retail/catalog/items/"
            "{item_id}/service-price-tiers"
        ):
            "post",
        (
            "/admin/retail/catalog/"
            "service-price-tiers/{tier_id}"
        ):
            {
                "patch",
                "delete",
            },
    }

    for path, methods in expected.items():
        assert path in paths

        available = set(
            paths[path].keys()
        )

        if isinstance(methods, str):
            methods = {methods}

        assert methods <= available
