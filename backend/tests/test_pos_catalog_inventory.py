from decimal import Decimal
from uuid import uuid4

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.services.pos_inventory_service import PosInventoryService


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
        sku=f"CATINV-{suffix}",
        base_price=Decimal("25.00"),
        sort_order=0,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _enable_product_for_branch(
    db_session,
    *,
    branch,
    product,
    is_available=True,
):
    setting = PosBranchProduct(
        branch_id=branch.id,
        product_id=product.id,
        price=None,
        is_available=is_available,
        sort_order=0,
    )
    db_session.add(setting)
    db_session.commit()
    return setting


def _track(
    db_session,
    *,
    branch,
    product,
    initial,
    threshold="2.000",
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


def _public_product(payload, product_id):
    for category in payload["categories"]:
        for product in category["products"]:
            if product["id"] == product_id:
                return product

    raise AssertionError(
        f"Product {product_id} missing from public catalog"
    )


def _admin_product(payload, product_id):
    return next(
        product
        for product in payload["products"]
        if product["id"] == product_id
    )


def _admin_branch(product_json, branch_id):
    return next(
        branch
        for branch in product_json["branches"]
        if branch["branch_id"] == branch_id
    )


def test_public_catalog_untracked_product_reports_untracked(
    client,
    db_session,
):
    branch = _create_branch(db_session, "public-untracked")
    product = _create_product(db_session, "Public Untracked")

    _enable_product_for_branch(
        db_session,
        branch=branch,
        product=product,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": branch.code},
    )

    assert response.status_code == 200

    product_json = _public_product(
        response.json(),
        product.id,
    )

    assert product_json["inventory"] == {
        "tracked": False,
        "quantity_available": None,
        "low_stock_threshold": None,
        "status": "UNTRACKED",
    }


def test_public_catalog_keeps_zero_stock_product_visible(
    client,
    db_session,
):
    branch = _create_branch(db_session, "public-zero")
    product = _create_product(db_session, "Public Zero")

    _enable_product_for_branch(
        db_session,
        branch=branch,
        product=product,
    )

    _track(
        db_session,
        branch=branch,
        product=product,
        initial="0.000",
        threshold="2.000",
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": branch.code},
    )

    assert response.status_code == 200

    product_json = _public_product(
        response.json(),
        product.id,
    )

    assert product_json["inventory"]["tracked"] is True
    assert (
        product_json["inventory"]["quantity_available"]
        == "0.000"
    )
    assert (
        product_json["inventory"]["low_stock_threshold"]
        == "2.000"
    )
    assert (
        product_json["inventory"]["status"]
        == "OUT_OF_STOCK"
    )


def test_public_catalog_inventory_is_branch_specific(
    client,
    db_session,
):
    branch_a = _create_branch(db_session, "public-a")
    branch_b = _create_branch(db_session, "public-b")
    product = _create_product(db_session, "Shared Public")

    _enable_product_for_branch(
        db_session,
        branch=branch_a,
        product=product,
    )
    _enable_product_for_branch(
        db_session,
        branch=branch_b,
        product=product,
    )

    _track(
        db_session,
        branch=branch_a,
        product=product,
        initial="3.000",
        threshold="2.000",
    )
    _track(
        db_session,
        branch=branch_b,
        product=product,
        initial="9.000",
        threshold="2.000",
    )

    response_a = client.get(
        "/pos/catalog",
        params={"branch_code": branch_a.code},
    )
    response_b = client.get(
        "/pos/catalog",
        params={"branch_code": branch_b.code},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    product_a = _public_product(
        response_a.json(),
        product.id,
    )
    product_b = _public_product(
        response_b.json(),
        product.id,
    )

    assert (
        product_a["inventory"]["quantity_available"]
        == "3.000"
    )
    assert (
        product_b["inventory"]["quantity_available"]
        == "9.000"
    )

    assert product_a["inventory"]["status"] == "AVAILABLE"
    assert product_b["inventory"]["status"] == "AVAILABLE"


def test_untracked_branch_does_not_inherit_other_branch_stock(
    client,
    db_session,
):
    branch_a = _create_branch(db_session, "tracked-a")
    branch_b = _create_branch(db_session, "untracked-b")
    product = _create_product(db_session, "Isolation Product")

    _enable_product_for_branch(
        db_session,
        branch=branch_a,
        product=product,
    )
    _enable_product_for_branch(
        db_session,
        branch=branch_b,
        product=product,
    )

    _track(
        db_session,
        branch=branch_a,
        product=product,
        initial="8.000",
    )

    response_a = client.get(
        "/pos/catalog",
        params={"branch_code": branch_a.code},
    )
    response_b = client.get(
        "/pos/catalog",
        params={"branch_code": branch_b.code},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    product_a = _public_product(
        response_a.json(),
        product.id,
    )
    product_b = _public_product(
        response_b.json(),
        product.id,
    )

    assert product_a["inventory"]["tracked"] is True
    assert (
        product_a["inventory"]["quantity_available"]
        == "8.000"
    )

    assert product_b["inventory"] == {
        "tracked": False,
        "quantity_available": None,
        "low_stock_threshold": None,
        "status": "UNTRACKED",
    }


def test_admin_catalog_exposes_inventory_separately_from_availability(
    client,
    db_session,
    super_headers,
):
    branch_zero = _create_branch(db_session, "admin-zero")
    branch_negative = _create_branch(
        db_session,
        "admin-negative",
    )
    branch_untracked = _create_branch(
        db_session,
        "admin-untracked",
    )
    product = _create_product(db_session, "Admin Inventory")

    _enable_product_for_branch(
        db_session,
        branch=branch_zero,
        product=product,
        is_available=False,
    )
    _enable_product_for_branch(
        db_session,
        branch=branch_negative,
        product=product,
        is_available=True,
    )
    _enable_product_for_branch(
        db_session,
        branch=branch_untracked,
        product=product,
        is_available=True,
    )

    _track(
        db_session,
        branch=branch_zero,
        product=product,
        initial="0.000",
        threshold="2.000",
    )

    negative_balance = _track(
        db_session,
        branch=branch_negative,
        product=product,
        initial="1.000",
        threshold="2.000",
    )

    PosInventoryService.record_waste(
        db_session,
        balance=negative_balance,
        quantity=Decimal("2.000"),
        note="Inventory test waste",
        admin_id=None,
    )
    db_session.commit()

    response = client.get(
        "/admin/pos/catalog",
        headers=super_headers,
    )

    assert response.status_code == 200

    product_json = _admin_product(
        response.json(),
        product.id,
    )

    zero = _admin_branch(
        product_json,
        branch_zero.id,
    )
    negative = _admin_branch(
        product_json,
        branch_negative.id,
    )
    untracked = _admin_branch(
        product_json,
        branch_untracked.id,
    )

    assert zero["is_available"] is False
    assert zero["inventory_tracked"] is True
    assert (
        zero["inventory_quantity_on_hand"]
        == "0.000"
    )
    assert (
        zero["inventory_low_stock_threshold"]
        == "2.000"
    )
    assert zero["inventory_status"] == "OUT_OF_STOCK"

    assert negative["is_available"] is True
    assert negative["inventory_tracked"] is True
    assert (
        negative["inventory_quantity_on_hand"]
        == "-1.000"
    )
    assert negative["inventory_status"] == "REVIEW"

    assert untracked["is_available"] is True
    assert untracked["inventory_tracked"] is False
    assert (
        untracked["inventory_quantity_on_hand"]
        is None
    )
    assert (
        untracked["inventory_low_stock_threshold"]
        is None
    )
    assert untracked["inventory_status"] == "UNTRACKED"
