from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.branch import Branch
from app.models.pos_catalog import PosCategory, PosProduct
from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)
from app.models.pos_orders import PosOrder, PosOrderItem
from app.services.pos_inventory_service import PosInventoryService


def _create_branch(db_session, suffix):
    branch = Branch(
        name=f"Branch {suffix}",
        code=f"branch-{suffix}",
    )
    db_session.add(branch)
    db_session.flush()
    return branch


def _create_product(db_session, suffix):
    category = PosCategory(
        name=f"Category {suffix}",
        slug=f"category-{suffix}",
    )
    db_session.add(category)
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Product {suffix}",
        sku=f"SKU-{suffix}",
        base_price=Decimal("10.00"),
    )
    db_session.add(product)
    db_session.flush()
    return product


def _create_order(
    db_session,
    *,
    branch,
    product,
    quantity,
    suffix,
):
    quantity_decimal = Decimal(quantity)

    order = PosOrder(
        order_uuid=f"00000000-0000-0000-0000-{suffix:0>12}",
        branch_id=branch.id,
        terminal_id="inventory-test",
        subtotal=Decimal("10.00") * quantity_decimal,
        total=Decimal("10.00") * quantity_decimal,
        created_at_client=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.flush()

    item = PosOrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        quantity=int(quantity_decimal),
        unit_base_price=Decimal("10.00"),
        unit_modifier_total=Decimal("0.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("10.00") * quantity_decimal,
    )
    db_session.add(item)
    db_session.flush()

    return order, item


def _configure(
    db_session,
    *,
    branch,
    product,
    initial,
    threshold=Decimal("2.000"),
):
    return PosInventoryService.configure_tracking(
        db_session,
        branch=branch,
        product=product,
        is_tracked=True,
        initial_quantity=Decimal(initial),
        low_stock_threshold=Decimal(threshold),
    )


@pytest.mark.parametrize(
    (
        "tracked",
        "quantity",
        "threshold",
        "expected",
    ),
    [
        (False, Decimal("50.000"), Decimal("5.000"), "UNTRACKED"),
        (True, Decimal("-0.001"), Decimal("5.000"), "REVIEW"),
        (True, Decimal("0.000"), Decimal("5.000"), "OUT_OF_STOCK"),
        (True, Decimal("3.000"), Decimal("5.000"), "LOW_STOCK"),
        (True, Decimal("5.000"), Decimal("5.000"), "LOW_STOCK"),
        (True, Decimal("5.001"), Decimal("5.000"), "AVAILABLE"),
    ],
)
def test_inventory_status_precedence(
    tracked,
    quantity,
    threshold,
    expected,
):
    assert (
        PosInventoryService.status_for(
            tracked=tracked,
            quantity_on_hand=quantity,
            threshold=threshold,
        )
        == expected
    )


def _balance_for(db_session, *, branch, product):
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


def _movements_for(db_session, item):
    return list(
        db_session.scalars(
            select(PosInventoryMovement)
            .where(
                PosInventoryMovement.inventory_item_id == item.id
            )
            .order_by(PosInventoryMovement.id)
        )
    )


def test_inventory_manual_movement_sequence(db_session):
    branch = _create_branch(db_session, "manual-sequence")
    product = _create_product(db_session, "manual-sequence")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("10.000"),
    )

    item, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
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
        note="Damaged product",
        admin_id=None,
    )

    PosInventoryService.adjust_count(
        db_session,
        balance=balance,
        physical_quantity=Decimal("9.000"),
        note="Physical count",
        admin_id=None,
    )

    db_session.flush()
    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal("9.000")

    movements = _movements_for(db_session, item)

    assert [
        (
            movement.movement_type,
            movement.quantity_delta,
            movement.balance_after,
        )
        for movement in movements
    ] == [
        ("INITIAL", Decimal("10.000"), Decimal("10.000")),
        ("RECEIPT", Decimal("5.000"), Decimal("15.000")),
        ("WASTE", Decimal("-2.000"), Decimal("13.000")),
        ("ADJUSTMENT", Decimal("-4.000"), Decimal("9.000")),
    ]


def test_disable_and_reenable_preserves_existing_quantity(
    db_session,
):
    branch = _create_branch(db_session, "reenable")
    product = _create_product(db_session, "reenable")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("10.000"),
        threshold=Decimal("2.000"),
    )

    PosInventoryService.configure_tracking(
        db_session,
        branch=branch,
        product=product,
        is_tracked=False,
        initial_quantity=None,
        low_stock_threshold=Decimal("3.000"),
    )

    item, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    assert balance.is_tracked is False
    assert balance.quantity_on_hand == Decimal("10.000")

    PosInventoryService.configure_tracking(
        db_session,
        branch=branch,
        product=product,
        is_tracked=True,
        initial_quantity=None,
        low_stock_threshold=Decimal("4.000"),
    )

    db_session.refresh(balance)

    assert balance.is_tracked is True
    assert balance.quantity_on_hand == Decimal("10.000")
    assert balance.low_stock_threshold == Decimal("4.000")

    movements = _movements_for(db_session, item)
    assert len(movements) == 1
    assert movements[0].movement_type == "INITIAL"


def test_first_enable_rejects_negative_initial_quantity(
    db_session,
):
    branch = _create_branch(db_session, "negative-initial")
    product = _create_product(db_session, "negative-initial")

    with pytest.raises(ValueError):
        _configure(
            db_session,
            branch=branch,
            product=product,
            initial=Decimal("-0.001"),
        )


def test_receipt_requires_positive_quantity(db_session):
    branch = _create_branch(db_session, "receipt-validation")
    product = _create_product(db_session, "receipt-validation")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("1.000"),
    )

    _, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    with pytest.raises(ValueError):
        PosInventoryService.record_receipt(
            db_session,
            balance=balance,
            quantity=Decimal("0.000"),
            note="Invalid receipt",
            admin_id=None,
        )


def test_waste_requires_positive_quantity_and_note(
    db_session,
):
    branch = _create_branch(db_session, "waste-validation")
    product = _create_product(db_session, "waste-validation")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("5.000"),
    )

    _, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    with pytest.raises(ValueError):
        PosInventoryService.record_waste(
            db_session,
            balance=balance,
            quantity=Decimal("0.000"),
            note="Damaged",
            admin_id=None,
        )

    with pytest.raises(ValueError):
        PosInventoryService.record_waste(
            db_session,
            balance=balance,
            quantity=Decimal("1.000"),
            note="   ",
            admin_id=None,
        )


def test_adjust_count_requires_note(db_session):
    branch = _create_branch(db_session, "adjust-validation")
    product = _create_product(db_session, "adjust-validation")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("5.000"),
    )

    _, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    with pytest.raises(ValueError):
        PosInventoryService.adjust_count(
            db_session,
            balance=balance,
            physical_quantity=Decimal("0.000"),
            note="",
            admin_id=None,
        )


def test_sale_and_reversal_are_idempotent(db_session):
    branch = _create_branch(db_session, "sale-idempotent")
    product = _create_product(db_session, "sale-idempotent")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("10.000"),
    )

    order, _ = _create_order(
        db_session,
        branch=branch,
        product=product,
        quantity=2,
        suffix=1,
    )

    PosInventoryService.apply_sale(
        db_session,
        order=order,
        allow_negative=False,
    )
    PosInventoryService.apply_sale(
        db_session,
        order=order,
        allow_negative=False,
    )

    item, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    db_session.refresh(balance)

    sales = [
        movement
        for movement in _movements_for(db_session, item)
        if movement.movement_type == "SALE"
    ]

    assert balance.quantity_on_hand == Decimal("8.000")
    assert len(sales) == 1
    assert sales[0].quantity_delta == Decimal("-2.000")

    PosInventoryService.reverse_sale(
        db_session,
        order=order,
        note="Refund",
        admin_id=None,
    )
    PosInventoryService.reverse_sale(
        db_session,
        order=order,
        note="Refund",
        admin_id=None,
    )

    db_session.refresh(balance)

    reversals = [
        movement
        for movement in _movements_for(db_session, item)
        if movement.movement_type == "SALE_REVERSAL"
    ]

    assert balance.quantity_on_hand == Decimal("10.000")
    assert len(reversals) == 1
    assert reversals[0].quantity_delta == Decimal("2.000")


def test_strict_sale_rejects_insufficient_stock_without_mutation(
    db_session,
):
    branch = _create_branch(db_session, "strict-sale")
    product = _create_product(db_session, "strict-sale")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("1.000"),
    )

    order, _ = _create_order(
        db_session,
        branch=branch,
        product=product,
        quantity=2,
        suffix=2,
    )

    item, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    with pytest.raises(HTTPException) as exc:
        PosInventoryService.apply_sale(
            db_session,
            order=order,
            allow_negative=False,
        )

    assert exc.value.status_code == 409

    db_session.refresh(balance)
    assert balance.quantity_on_hand == Decimal("1.000")

    sales = [
        movement
        for movement in _movements_for(db_session, item)
        if movement.movement_type == "SALE"
    ]
    assert sales == []


def test_offline_sale_may_make_balance_negative(db_session):
    branch = _create_branch(db_session, "offline-sale")
    product = _create_product(db_session, "offline-sale")

    _configure(
        db_session,
        branch=branch,
        product=product,
        initial=Decimal("1.000"),
    )

    order, _ = _create_order(
        db_session,
        branch=branch,
        product=product,
        quantity=3,
        suffix=3,
    )

    PosInventoryService.apply_sale(
        db_session,
        order=order,
        allow_negative=True,
    )

    _, balance = _balance_for(
        db_session,
        branch=branch,
        product=product,
    )

    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal("-2.000")
    assert (
        PosInventoryService.status_for(
            tracked=balance.is_tracked,
            quantity_on_hand=balance.quantity_on_hand,
            threshold=balance.low_stock_threshold,
        )
        == "REVIEW"
    )


def test_branch_mutation_does_not_change_other_branch(
    db_session,
):
    branch_a = _create_branch(db_session, "branch-a")
    branch_b = _create_branch(db_session, "branch-b")
    product = _create_product(db_session, "shared-product")

    _configure(
        db_session,
        branch=branch_a,
        product=product,
        initial=Decimal("10.000"),
    )
    _configure(
        db_session,
        branch=branch_b,
        product=product,
        initial=Decimal("20.000"),
    )

    order, _ = _create_order(
        db_session,
        branch=branch_a,
        product=product,
        quantity=3,
        suffix=4,
    )

    PosInventoryService.apply_sale(
        db_session,
        order=order,
        allow_negative=False,
    )

    _, balance_a = _balance_for(
        db_session,
        branch=branch_a,
        product=product,
    )
    _, balance_b = _balance_for(
        db_session,
        branch=branch_b,
        product=product,
    )

    db_session.refresh(balance_a)
    db_session.refresh(balance_b)

    assert balance_a.quantity_on_hand == Decimal("7.000")
    assert balance_b.quantity_on_hand == Decimal("20.000")
