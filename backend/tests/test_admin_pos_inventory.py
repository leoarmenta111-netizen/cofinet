from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.branch import Branch
from app.models.pos_catalog import PosCategory, PosProduct
from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)
from app.services.pos_inventory_service import PosInventoryService


def _decimal(value):
    return Decimal(str(value))


def _create_branch(db_session, label):
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


def _create_product(db_session, label):
    suffix = uuid4().hex[:8]

    category = PosCategory(
        name=f"Category {label} {suffix}",
        slug=f"category-{suffix}",
        sort_order=0,
        is_active=True,
    )
    db_session.add(category)
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"{label} {suffix}",
        sku=f"INV-{suffix}",
        base_price=Decimal("10.00"),
        sort_order=0,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _inventory_for(db_session, *, branch, product):
    item = db_session.scalar(
        select(PosInventoryItem).where(
            PosInventoryItem.product_id == product.id
        )
    )
    assert item is not None

    balance = db_session.scalar(
        select(PosInventoryBalance).where(
            PosInventoryBalance.branch_id == branch.id,
            PosInventoryBalance.inventory_item_id == item.id,
        )
    )
    assert balance is not None

    return item, balance


def _enable_tracking(
    db_session,
    *,
    branch,
    product,
    initial,
    threshold=Decimal("2.000"),
):
    PosInventoryService.configure_tracking(
        db_session,
        branch=branch,
        product=product,
        is_tracked=True,
        initial_quantity=Decimal(initial),
        low_stock_threshold=Decimal(threshold),
    )
    db_session.commit()

    return _inventory_for(
        db_session,
        branch=branch,
        product=product,
    )


def _initial_movements(db_session, *, item, branch):
    return list(
        db_session.scalars(
            select(PosInventoryMovement).where(
                PosInventoryMovement.inventory_item_id == item.id,
                PosInventoryMovement.branch_id == branch.id,
                PosInventoryMovement.movement_type == "INITIAL",
            )
        )
    )


def test_inventory_receipt_requires_authentication(
    client,
    db_session,
):
    branch = _create_branch(db_session, "Auth")
    product = _create_product(db_session, "Auth Product")

    item, _ = _enable_tracking(
        db_session,
        branch=branch,
        product=product,
        initial="10.000",
    )

    response = client.post(
        f"/admin/pos/inventory/{item.id}/receipt",
        json={
            "branch_code": branch.code,
            "quantity": "5.000",
            "note": "Compra semanal",
        },
    )

    assert response.status_code == 401


def test_first_tracking_enable_requires_initial_quantity(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session, "Initial")
    product = _create_product(db_session, "Initial Product")

    response = client.put(
        (
            f"/admin/pos/inventory/products/{product.id}"
            f"/branches/{branch.code}"
        ),
        headers=super_headers,
        json={
            "is_tracked": True,
            "low_stock_threshold": "2.000",
            "initial_quantity": None,
        },
    )

    assert response.status_code == 422


def test_tracking_enable_disable_reenable_preserves_stock(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session, "Tracking")
    product = _create_product(db_session, "Tracking Product")

    enable = client.put(
        (
            f"/admin/pos/inventory/products/{product.id}"
            f"/branches/{branch.code}"
        ),
        headers=super_headers,
        json={
            "is_tracked": True,
            "low_stock_threshold": "2.000",
            "initial_quantity": "10.000",
        },
    )

    assert enable.status_code == 200

    enabled = enable.json()
    assert enabled["is_tracked"] is True
    assert _decimal(enabled["quantity_on_hand"]) == Decimal(
        "10.000"
    )

    item, balance = _inventory_for(
        db_session,
        branch=branch,
        product=product,
    )

    assert len(
        _initial_movements(
            db_session,
            item=item,
            branch=branch,
        )
    ) == 1

    disable = client.put(
        (
            f"/admin/pos/inventory/products/{product.id}"
            f"/branches/{branch.code}"
        ),
        headers=super_headers,
        json={
            "is_tracked": False,
            "low_stock_threshold": "3.000",
            "initial_quantity": None,
        },
    )

    assert disable.status_code == 200
    disabled = disable.json()

    assert disabled["is_tracked"] is False
    assert _decimal(disabled["quantity_on_hand"]) == Decimal(
        "10.000"
    )

    reenable = client.put(
        (
            f"/admin/pos/inventory/products/{product.id}"
            f"/branches/{branch.code}"
        ),
        headers=super_headers,
        json={
            "is_tracked": True,
            "low_stock_threshold": "4.000",
            "initial_quantity": None,
        },
    )

    assert reenable.status_code == 200
    reen = reenable.json()

    assert reen["is_tracked"] is True
    assert _decimal(reen["quantity_on_hand"]) == Decimal(
        "10.000"
    )
    assert _decimal(reen["low_stock_threshold"]) == Decimal(
        "4.000"
    )

    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal("10.000")
    assert len(
        _initial_movements(
            db_session,
            item=item,
            branch=branch,
        )
    ) == 1


def test_inventory_list_filters_branch_and_detail_isolated(
    client,
    db_session,
    super_headers,
):
    branch_a = _create_branch(db_session, "ListA")
    branch_b = _create_branch(db_session, "ListB")
    product = _create_product(db_session, "Shared Product")

    item, _ = _enable_tracking(
        db_session,
        branch=branch_a,
        product=product,
        initial="10.000",
    )

    _enable_tracking(
        db_session,
        branch=branch_b,
        product=product,
        initial="20.000",
    )

    response = client.get(
        "/admin/pos/inventory",
        params={"branch_code": branch_a.code},
        headers=super_headers,
    )

    assert response.status_code == 200

    rows = response.json()
    assert rows
    assert all(
        row["branch_code"] == branch_a.code
        for row in rows
    )

    row = next(
        row
        for row in rows
        if row["item_id"] == item.id
    )

    assert row["product_id"] == product.id
    assert _decimal(row["quantity_on_hand"]) == Decimal(
        "10.000"
    )

    detail_a = client.get(
        f"/admin/pos/inventory/{item.id}",
        params={"branch_code": branch_a.code},
        headers=super_headers,
    )
    detail_b = client.get(
        f"/admin/pos/inventory/{item.id}",
        params={"branch_code": branch_b.code},
        headers=super_headers,
    )

    assert detail_a.status_code == 200
    assert detail_b.status_code == 200

    assert detail_a.json()["branch_code"] == branch_a.code
    assert _decimal(
        detail_a.json()["quantity_on_hand"]
    ) == Decimal("10.000")

    assert detail_b.json()["branch_code"] == branch_b.code
    assert _decimal(
        detail_b.json()["quantity_on_hand"]
    ) == Decimal("20.000")


def test_inventory_movements_are_newest_first(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session, "History")
    product = _create_product(db_session, "History Product")

    item, balance = _enable_tracking(
        db_session,
        branch=branch,
        product=product,
        initial="10.000",
    )

    PosInventoryService.record_receipt(
        db_session,
        balance=balance,
        quantity=Decimal("5.000"),
        note="Delivery",
        admin_id=None,
    )

    PosInventoryService.record_waste(
        db_session,
        balance=balance,
        quantity=Decimal("2.000"),
        note="Damaged",
        admin_id=None,
    )

    db_session.commit()

    response = client.get(
        f"/admin/pos/inventory/{item.id}/movements",
        params={"branch_code": branch.code},
        headers=super_headers,
    )

    assert response.status_code == 200

    movements = response.json()

    assert [
        movement["movement_type"]
        for movement in movements[:3]
    ] == [
        "WASTE",
        "RECEIPT",
        "INITIAL",
    ]

    ids = [
        movement["id"]
        for movement in movements
    ]
    assert ids == sorted(ids, reverse=True)


def test_manual_inventory_mutations_update_stock(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session, "Manual")
    product = _create_product(db_session, "Manual Product")

    item, _ = _enable_tracking(
        db_session,
        branch=branch,
        product=product,
        initial="10.000",
    )

    receipt = client.post(
        f"/admin/pos/inventory/{item.id}/receipt",
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "quantity": "5.000",
            "note": "Compra semanal",
        },
    )

    assert receipt.status_code == 200
    assert _decimal(
        receipt.json()["quantity_on_hand"]
    ) == Decimal("15.000")

    waste = client.post(
        f"/admin/pos/inventory/{item.id}/waste",
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "quantity": "2.000",
            "note": "Producto dañado",
        },
    )

    assert waste.status_code == 200
    assert _decimal(
        waste.json()["quantity_on_hand"]
    ) == Decimal("13.000")

    adjust = client.post(
        f"/admin/pos/inventory/{item.id}/adjust",
        headers=super_headers,
        json={
            "branch_code": branch.code,
            "physical_quantity": "9.000",
            "note": "Conteo físico",
        },
    )

    assert adjust.status_code == 200
    assert _decimal(
        adjust.json()["quantity_on_hand"]
    ) == Decimal("9.000")

    movements = list(
        db_session.scalars(
            select(PosInventoryMovement)
            .where(
                PosInventoryMovement.inventory_item_id
                == item.id,
                PosInventoryMovement.branch_id
                == branch.id,
            )
            .order_by(PosInventoryMovement.id)
        )
    )

    assert [
        (
            movement.movement_type,
            movement.quantity_delta,
            movement.balance_after,
        )
        for movement in movements
    ] == [
        (
            "INITIAL",
            Decimal("10.000"),
            Decimal("10.000"),
        ),
        (
            "RECEIPT",
            Decimal("5.000"),
            Decimal("15.000"),
        ),
        (
            "WASTE",
            Decimal("-2.000"),
            Decimal("13.000"),
        ),
        (
            "ADJUSTMENT",
            Decimal("-4.000"),
            Decimal("9.000"),
        ),
    ]


def test_manual_mutation_rejects_wrong_branch_item_combination(
    client,
    db_session,
    super_headers,
):
    branch_a = _create_branch(db_session, "WrongA")
    branch_b = _create_branch(db_session, "WrongB")
    product = _create_product(db_session, "Wrong Product")

    item, balance_a = _enable_tracking(
        db_session,
        branch=branch_a,
        product=product,
        initial="10.000",
    )

    response = client.post(
        f"/admin/pos/inventory/{item.id}/receipt",
        headers=super_headers,
        json={
            "branch_code": branch_b.code,
            "quantity": "5.000",
            "note": "Wrong branch",
        },
    )

    assert response.status_code == 404

    db_session.refresh(balance_a)
    assert balance_a.quantity_on_hand == Decimal("10.000")


def test_tracking_returns_404_for_missing_product_or_branch(
    client,
    db_session,
    super_headers,
):
    branch = _create_branch(db_session, "Missing")
    product = _create_product(db_session, "Missing Product")

    missing_product = client.put(
        (
            "/admin/pos/inventory/products/999999999"
            f"/branches/{branch.code}"
        ),
        headers=super_headers,
        json={
            "is_tracked": True,
            "low_stock_threshold": "2.000",
            "initial_quantity": "10.000",
        },
    )

    assert missing_product.status_code == 404

    missing_branch = client.put(
        (
            f"/admin/pos/inventory/products/{product.id}"
            "/branches/does-not-exist"
        ),
        headers=super_headers,
        json={
            "is_tracked": True,
            "low_stock_threshold": "2.000",
            "initial_quantity": "10.000",
        },
    )

    assert missing_branch.status_code == 404


def test_admin_inventory_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected_methods = {
        "/admin/pos/inventory": "get",
        "/admin/pos/inventory/{item_id}": "get",
        "/admin/pos/inventory/{item_id}/movements": "get",
        (
            "/admin/pos/inventory/products/{product_id}"
            "/branches/{branch_code}"
        ): "put",
        "/admin/pos/inventory/{item_id}/receipt": "post",
        "/admin/pos/inventory/{item_id}/waste": "post",
        "/admin/pos/inventory/{item_id}/adjust": "post",
    }

    for path, method in expected_methods.items():
        assert path in paths
        assert method in paths[path]


def test_admin_inventory_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected_methods = {
        "/admin/pos/inventory": "get",
        "/admin/pos/inventory/{item_id}": "get",
        "/admin/pos/inventory/{item_id}/movements": "get",
        (
            "/admin/pos/inventory/products/{product_id}"
            "/branches/{branch_code}"
        ): "put",
        "/admin/pos/inventory/{item_id}/receipt": "post",
        "/admin/pos/inventory/{item_id}/waste": "post",
        "/admin/pos/inventory/{item_id}/adjust": "post",
    }

    for path, method in expected_methods.items():
        assert path in paths
        assert method in paths[path]
