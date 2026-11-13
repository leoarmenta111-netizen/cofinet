from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)


def _decimal(value):
    return Decimal(str(value))


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


def _product_with_inventory(
    db_session,
    *,
    branch,
    label,
    quantity="10.000",
    threshold="2.000",
):
    suffix = uuid4().hex[:8]

    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=f"RET-{suffix}",
        name=f"{label} {suffix}",
        description=None,
        category="Test",
        base_unit_code="PIECE",
        cost=Decimal("5.00"),
        inventory_tracked=True,
        low_stock_threshold=Decimal(
            threshold
        ),
        max_stock=Decimal("100.000"),
        is_active=True,
    )

    db_session.add(item)
    db_session.flush()

    balance = RetailInventoryBalance(
        branch_id=branch.id,
        item_id=item.id,
        quantity_on_hand=Decimal(
            quantity
        ),
        low_stock_threshold=Decimal(
            threshold
        ),
        max_stock=Decimal("100.000"),
    )

    db_session.add(balance)
    db_session.commit()
    db_session.refresh(item)
    db_session.refresh(balance)

    return item, balance


def test_admin_retail_inventory_requires_authentication(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "RetailAuth",
    )

    response = client.get(
        "/admin/retail/inventory",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 401


def test_admin_retail_inventory_list_and_detail_are_branch_scoped(
    client,
    db_session,
    super_headers,
):
    branch_a = _branch(
        db_session,
        "RetailListA",
    )

    branch_b = _branch(
        db_session,
        "RetailListB",
    )

    item_a, _ = _product_with_inventory(
        db_session,
        branch=branch_a,
        label="Product A",
        quantity="10.000",
    )

    _product_with_inventory(
        db_session,
        branch=branch_b,
        label="Product B",
        quantity="20.000",
    )

    response = client.get(
        "/admin/retail/inventory",
        params={
            "branch_code": branch_a.code,
        },
        headers=super_headers,
    )

    assert response.status_code == 200

    rows = response.json()

    assert len(rows) == 1
    assert rows[0]["item_id"] == item_a.id
    assert (
        rows[0]["branch_code"]
        == branch_a.code
    )
    assert (
        _decimal(
            rows[0]["quantity_on_hand"]
        )
        == Decimal("10.000")
    )
    assert rows[0]["status"] == "AVAILABLE"

    detail = client.get(
        (
            f"/admin/retail/inventory/"
            f"{item_a.id}"
        ),
        params={
            "branch_code": branch_a.code,
        },
        headers=super_headers,
    )

    assert detail.status_code == 200
    assert detail.json()["item_id"] == item_a.id

    wrong_branch = client.get(
        (
            f"/admin/retail/inventory/"
            f"{item_a.id}"
        ),
        params={
            "branch_code": branch_b.code,
        },
        headers=super_headers,
    )

    assert wrong_branch.status_code == 404


def test_admin_retail_inventory_entry_is_idempotent_and_audited(
    client,
    db_session,
    super_headers,
    super_admin,
):
    branch = _branch(
        db_session,
        "RetailEntry",
    )

    item, balance = _product_with_inventory(
        db_session,
        branch=branch,
        label="Entry Product",
        quantity="10.000",
    )

    payload = {
        "branch_code": branch.code,
        "quantity": "5.000",
        "note": "Supplier delivery",
        "idempotency_key": (
            "delivery-001"
        ),
    }

    first = client.post(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/entry"
        ),
        json=payload,
        headers=super_headers,
    )

    assert first.status_code == 200
    assert (
        _decimal(
            first.json()["quantity_on_hand"]
        )
        == Decimal("15.000")
    )

    replay = client.post(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/entry"
        ),
        json=payload,
        headers=super_headers,
    )

    assert replay.status_code == 200

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("15.000")
    )

    movements = list(
        db_session.scalars(
            select(
                RetailInventoryMovement
            ).where(
                RetailInventoryMovement.item_id
                == item.id,
                RetailInventoryMovement.movement_type
                == "MANUAL_ENTRY",
            )
        )
    )

    assert len(movements) == 1

    movement = movements[0]

    assert (
        movement.quantity_delta
        == Decimal("5.000")
    )
    assert (
        movement.created_by_admin_id
        == super_admin.id
    )
    assert movement.idempotency_key.startswith(
        "admin-retail:entry:"
    )


def test_admin_retail_inventory_removal_and_adjustment(
    client,
    db_session,
    super_headers,
    super_admin,
):
    branch = _branch(
        db_session,
        "RetailManual",
    )

    item, balance = _product_with_inventory(
        db_session,
        branch=branch,
        label="Manual Product",
        quantity="10.000",
    )

    removal = client.post(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/removal"
        ),
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "quantity": "2.000",
            "note": "Damaged item",
            "idempotency_key": (
                "removal-001"
            ),
        },
    )

    assert removal.status_code == 200
    assert (
        _decimal(
            removal.json()[
                "quantity_on_hand"
            ]
        )
        == Decimal("8.000")
    )

    adjust = client.post(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/adjust"
        ),
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "physical_quantity": "6.000",
            "note": "Physical count",
            "idempotency_key": (
                "adjust-001"
            ),
        },
    )

    assert adjust.status_code == 200
    assert (
        _decimal(
            adjust.json()[
                "quantity_on_hand"
            ]
        )
        == Decimal("6.000")
    )

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("6.000")
    )

    movements = list(
        db_session.scalars(
            select(
                RetailInventoryMovement
            )
            .where(
                RetailInventoryMovement.item_id
                == item.id
            )
            .order_by(
                RetailInventoryMovement.id
            )
        )
    )

    assert [
        movement.movement_type
        for movement in movements
    ] == [
        "MANUAL_REMOVAL",
        "ADJUSTMENT",
    ]

    assert [
        movement.quantity_delta
        for movement in movements
    ] == [
        Decimal("-2.000"),
        Decimal("-2.000"),
    ]

    assert all(
        movement.created_by_admin_id
        == super_admin.id
        for movement in movements
    )


def test_admin_retail_inventory_removal_cannot_go_negative(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "RetailNegative",
    )

    item, balance = _product_with_inventory(
        db_session,
        branch=branch,
        label="Negative Product",
        quantity="3.000",
    )

    response = client.post(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/removal"
        ),
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "quantity": "4.000",
            "note": "Too much",
            "idempotency_key": (
                "negative-001"
            ),
        },
    )

    assert response.status_code == 409

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("3.000")
    )

    movements = list(
        db_session.scalars(
            select(
                RetailInventoryMovement
            ).where(
                RetailInventoryMovement.item_id
                == item.id
            )
        )
    )

    assert movements == []


def test_admin_retail_inventory_movements_are_newest_first(
    client,
    db_session,
    super_headers,
):
    branch = _branch(
        db_session,
        "RetailHistory",
    )

    item, _ = _product_with_inventory(
        db_session,
        branch=branch,
        label="History Product",
        quantity="10.000",
    )

    for key, quantity in (
        ("entry-a", "1.000"),
        ("entry-b", "2.000"),
    ):
        response = client.post(
            (
                f"/admin/retail/inventory/"
                f"{item.id}/entry"
            ),
            headers=super_headers,
            json={
                "branch_code": branch.code,
                "quantity": quantity,
                "note": key,
                "idempotency_key": key,
            },
        )

        assert response.status_code == 200

    response = client.get(
        (
            f"/admin/retail/inventory/"
            f"{item.id}/movements"
        ),
        params={
            "branch_code": branch.code,
        },
        headers=super_headers,
    )

    assert response.status_code == 200

    movements = response.json()

    assert len(movements) == 2
    assert movements[0]["id"] > movements[1]["id"]
    assert (
        movements[0]["movement_type"]
        == "MANUAL_ENTRY"
    )


def test_admin_retail_inventory_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected_methods = {
        "/admin/retail/inventory":
            "get",
        "/admin/retail/inventory/{item_id}":
            "get",
        (
            "/admin/retail/inventory/"
            "{item_id}/movements"
        ):
            "get",
        (
            "/admin/retail/inventory/"
            "{item_id}/entry"
        ):
            "post",
        (
            "/admin/retail/inventory/"
            "{item_id}/removal"
        ):
            "post",
        (
            "/admin/retail/inventory/"
            "{item_id}/adjust"
        ):
            "post",
    }

    for path, method in (
        expected_methods.items()
    ):
        assert path in paths
        assert method in paths[path]
