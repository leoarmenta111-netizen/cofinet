from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
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


def _create_product(
    client,
    headers,
    *,
    branch,
    sku,
    tracked=True,
):
    return client.post(
        "/admin/retail/catalog/items",
        headers=headers,
        json={
            "branch_id": branch.id,
            "item_type": "PRODUCT",
            "sku": sku,
            "name": f"Product {sku}",
            "description": None,
            "category": "Office",
            "base_unit_code": "PIECE",
            "cost": "5.00",
            "inventory_tracked": tracked,
            "low_stock_threshold": (
                "2.000"
                if tracked
                else None
            ),
            "max_stock": (
                "100.000"
                if tracked
                else None
            ),
            "is_active": True,
        },
    )


def test_admin_retail_catalog_requires_authentication(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "CatalogAuth",
    )

    response = client.get(
        "/admin/retail/catalog",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 401


def test_admin_retail_catalog_create_tracked_product_creates_zero_balance(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "CatalogCreate",
    )

    response = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="PAPER-001",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sku"] == "PAPER-001"
    assert data["inventory_tracked"] is True

    balance = db_session.execute(
        select(
            RetailInventoryBalance
        ).where(
            RetailInventoryBalance.item_id
            == data["id"]
        )
    ).scalar_one()

    assert (
        balance.quantity_on_hand
        == Decimal("0.000")
    )
    assert (
        balance.low_stock_threshold
        == Decimal("2.000")
    )


def test_admin_retail_catalog_rejects_inventory_for_service(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "CatalogService",
    )

    response = client.post(
        "/admin/retail/catalog/items",
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "item_type": "SERVICE",
            "sku": "PRINT-001",
            "name": "Printing",
            "description": None,
            "category": "Services",
            "base_unit_code": "PAGE",
            "cost": "0.00",
            "inventory_tracked": True,
            "low_stock_threshold": "1.000",
            "max_stock": "10.000",
            "is_active": True,
        },
    )

    assert response.status_code == 422


def test_admin_retail_catalog_rejects_duplicate_sku_per_branch(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "CatalogSku",
    )

    first = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="DUP-001",
    )

    assert first.status_code == 200

    second = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="DUP-001",
    )

    assert second.status_code == 409


def test_admin_retail_catalog_update_syncs_inventory_settings(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "CatalogUpdate",
    )

    created = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="UPDATE-001",
        tracked=False,
    )

    assert created.status_code == 200

    item_id = created.json()["id"]

    no_balance = db_session.execute(
        select(
            RetailInventoryBalance
        ).where(
            RetailInventoryBalance.item_id
            == item_id
        )
    ).scalar_one_or_none()

    assert no_balance is None

    updated = client.patch(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}"
        ),
        headers=super_headers,
        json={
            "inventory_tracked": True,
            "low_stock_threshold": "4.000",
            "max_stock": "80.000",
            "cost": "6.50",
        },
    )

    assert updated.status_code == 200

    balance = db_session.execute(
        select(
            RetailInventoryBalance
        ).where(
            RetailInventoryBalance.item_id
            == item_id
        )
    ).scalar_one()

    assert (
        balance.quantity_on_hand
        == Decimal("0.000")
    )
    assert (
        balance.low_stock_threshold
        == Decimal("4.000")
    )
    assert (
        balance.max_stock
        == Decimal("80.000")
    )


def test_admin_retail_catalog_list_is_branch_scoped_and_includes_inactive(
    client,
    db_session,
    super_headers,
):
    branch_a = _branch(
        db_session,
        "CatalogListA",
    )

    branch_b = _branch(
        db_session,
        "CatalogListB",
    )

    created_a = _create_product(
        client,
        super_headers,
        branch=branch_a,
        sku="LIST-A",
    )

    created_b = _create_product(
        client,
        super_headers,
        branch=branch_b,
        sku="LIST-B",
    )

    assert created_a.status_code == 200
    assert created_b.status_code == 200

    item_a = created_a.json()["id"]

    inactive = client.patch(
        (
            "/admin/retail/catalog/items/"
            f"{item_a}"
        ),
        headers=super_headers,
        json={
            "is_active": False,
        },
    )

    assert inactive.status_code == 200

    response = client.get(
        "/admin/retail/catalog",
        headers=super_headers,
        params={
            "branch_code": branch_a.code,
        },
    )

    assert response.status_code == 200

    rows = response.json()

    assert len(rows) == 1
    assert rows[0]["sku"] == "LIST-A"
    assert rows[0]["is_active"] is False


def test_admin_retail_presentations_enforce_one_default_and_unique_barcode(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "Presentation",
    )

    product = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="PRESENT-001",
    )

    assert product.status_code == 200

    item_id = product.json()["id"]

    first = client.post(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}/presentations"
        ),
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "name": "Piece",
            "barcode": "750000001",
            "conversion_factor": "1.000",
            "sale_price": "10.00",
            "bulk_price": None,
            "bulk_min_quantity": None,
            "is_default": True,
            "is_active": True,
        },
    )

    assert first.status_code == 200

    second = client.post(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}/presentations"
        ),
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "name": "Box",
            "barcode": "750000002",
            "conversion_factor": "12.000",
            "sale_price": "100.00",
            "bulk_price": None,
            "bulk_min_quantity": None,
            "is_default": True,
            "is_active": True,
        },
    )

    assert second.status_code == 200

    presentations = list(
        db_session.scalars(
            select(RetailPresentation)
            .where(
                RetailPresentation.item_id
                == item_id
            )
            .order_by(
                RetailPresentation.id
            )
        )
    )

    assert [
        presentation.is_default
        for presentation in presentations
    ] == [
        False,
        True,
    ]

    duplicate = client.post(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}/presentations"
        ),
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "name": "Duplicate",
            "barcode": "750000002",
            "conversion_factor": "1.000",
            "sale_price": "9.00",
            "bulk_price": None,
            "bulk_min_quantity": None,
            "is_default": False,
            "is_active": True,
        },
    )

    assert duplicate.status_code == 409


def test_admin_retail_presentation_can_update_price_and_bulk_pricing(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "PresentationUpdate",
    )

    product = _create_product(
        client,
        super_headers,
        branch=branch,
        sku="PRICE-001",
    )

    item_id = product.json()["id"]

    created = client.post(
        (
            "/admin/retail/catalog/items/"
            f"{item_id}/presentations"
        ),
        headers=super_headers,
        json={
            "branch_id": branch.id,
            "name": "Piece",
            "barcode": "760000001",
            "conversion_factor": "1.000",
            "sale_price": "10.00",
            "bulk_price": None,
            "bulk_min_quantity": None,
            "is_default": True,
            "is_active": True,
        },
    )

    assert created.status_code == 200

    presentation_id = (
        created.json()["id"]
    )

    updated = client.patch(
        (
            "/admin/retail/catalog/"
            "presentations/"
            f"{presentation_id}"
        ),
        headers=super_headers,
        json={
            "sale_price": "12.50",
            "bulk_price": "10.00",
            "bulk_min_quantity": "10.000",
        },
    )

    assert updated.status_code == 200

    data = updated.json()

    assert (
        Decimal(str(data["sale_price"]))
        == Decimal("12.50")
    )
    assert (
        Decimal(str(data["bulk_price"]))
        == Decimal("10.00")
    )


def test_admin_retail_catalog_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected = {
        "/admin/retail/catalog":
            "get",
        "/admin/retail/catalog/items":
            "post",
        (
            "/admin/retail/catalog/"
            "items/{item_id}"
        ):
            "patch",
        (
            "/admin/retail/catalog/"
            "items/{item_id}/presentations"
        ):
            "post",
        (
            "/admin/retail/catalog/"
            "presentations/{presentation_id}"
        ):
            "patch",
    }

    for path, method in expected.items():
        assert path in paths
        assert method in paths[path]
