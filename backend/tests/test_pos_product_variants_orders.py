from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosBranchProductVariant,
    PosCategory,
    PosProduct,
    PosProductVariant,
    PosVariant,
    PosVariantGroup,
)
from app.schemas.pos_orders import (
    PosOrderCreate,
    PosOrderItemCreate,
)
from app.services.pos_order_service import PosOrderService


def seed_variant_product(db):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Ixtapa Test {suffix}",
        code=f"ixtapa-test-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Bebidas {suffix}",
        slug=f"bebidas-{suffix}",
        is_active=True,
    )

    group = PosVariantGroup(
        name=f"Tamaños Café {suffix}",
        sort_order=0,
        is_active=True,
    )

    db.add_all([
        branch,
        category,
        group,
    ])
    db.flush()

    product = PosProduct(
        category_id=category.id,
        variant_group_id=group.id,
        name=f"Latte {suffix}",
        base_price=Decimal("10.00"),
        preparation_station="BAR",
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

    small = PosVariant(
        variant_group_id=group.id,
        name="Chico 12 oz",
        sort_order=10,
        is_active=True,
    )

    large = PosVariant(
        variant_group_id=group.id,
        name="Grande 20 oz",
        sort_order=20,
        is_active=True,
    )

    db.add_all([small, large])
    db.flush()

    small_link = PosProductVariant(
        product_id=product.id,
        variant_id=small.id,
        price=Decimal("60.00"),
        is_active=True,
        sort_order=10,
    )

    large_link = PosProductVariant(
        product_id=product.id,
        variant_id=large.id,
        price=Decimal("80.00"),
        is_active=True,
        sort_order=20,
    )

    db.add_all([
        small_link,
        large_link,
    ])
    db.commit()

    return {
        "branch": branch,
        "product": product,
        "group": group,
        "small": small_link,
        "large": large_link,
    }


def seed_non_variant_product(db):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Plain Branch {suffix}",
        code=f"plain-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Plain Drinks {suffix}",
        slug=f"plain-drinks-{suffix}",
        is_active=True,
    )

    db.add_all([branch, category])
    db.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Agua {suffix}",
        base_price=Decimal("25.00"),
        preparation_station="NONE",
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

    db.commit()

    return branch, product


def order_payload(
    branch,
    product,
    *,
    product_variant_id=None,
):
    now = datetime.now(timezone.utc)

    item = {
        "product_id": product.id,
        "quantity": 1,
    }

    if product_variant_id is not None:
        item["product_variant_id"] = product_variant_id

    return PosOrderCreate(
        order_uuid=uuid4(),
        branch_code=branch.code,
        terminal_id="VARIANT-TEST-01",
        created_at_client=now,
        items=[item],
        payment={
            "payment_uuid": uuid4(),
            "method": "CASH",
            "amount_tendered": "500.00",
            "created_at_client": now,
        },
    )


def test_order_item_schema_accepts_product_variant_id():
    assert (
        "product_variant_id"
        in PosOrderItemCreate.model_fields
    )


def test_variant_product_requires_variant_selection(
    db_session,
):
    seeded = seed_variant_product(db_session)

    payload = order_payload(
        seeded["branch"],
        seeded["product"],
    )

    with pytest.raises(HTTPException) as error:
        PosOrderService.create(
            db_session,
            payload,
        )

    assert error.value.status_code == 400


def test_selected_variant_uses_server_variant_price(
    db_session,
):
    seeded = seed_variant_product(db_session)

    payload = order_payload(
        seeded["branch"],
        seeded["product"],
        product_variant_id=seeded["large"].id,
    )

    result = PosOrderService.create(
        db_session,
        payload,
    )

    assert (
        Decimal(result.items[0].unit_price)
        == Decimal("80.00")
    )

    assert (
        result.items[0].product_variant_id
        == seeded["large"].id
    )

    assert (
        result.items[0].variant_name
        == "Grande 20 oz"
    )


def test_branch_override_replaces_variant_price(
    db_session,
):
    seeded = seed_variant_product(db_session)

    db_session.add(
        PosBranchProductVariant(
            branch_id=seeded["branch"].id,
            product_variant_id=seeded["large"].id,
            price_override=Decimal("89.00"),
            is_available=True,
        )
    )
    db_session.commit()

    payload = order_payload(
        seeded["branch"],
        seeded["product"],
        product_variant_id=seeded["large"].id,
    )

    result = PosOrderService.create(
        db_session,
        payload,
    )

    assert (
        Decimal(result.items[0].unit_price)
        == Decimal("89.00")
    )


def test_non_variant_product_rejects_stray_variant(
    db_session,
):
    branch, product = seed_non_variant_product(
        db_session
    )

    payload = order_payload(
        branch,
        product,
        product_variant_id=999999,
    )

    with pytest.raises(HTTPException) as error:
        PosOrderService.create(
            db_session,
            payload,
        )

    assert error.value.status_code == 400
