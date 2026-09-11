from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.branch import Branch
from app.models.pos_catalog import PosCategory, PosProduct
from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)


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


def _create_branch(db_session, suffix):
    branch = Branch(
        name=f"Branch {suffix}",
        code=f"branch-{suffix}",
    )
    db_session.add(branch)
    db_session.flush()
    return branch


def _create_item(db_session, suffix):
    product = _create_product(db_session, suffix)
    item = PosInventoryItem(
        product_id=product.id,
        name=product.name,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_inventory_item_product_id_is_unique(db_session):
    product = _create_product(db_session, "item-unique")

    first = PosInventoryItem(
        product_id=product.id,
        name="First item",
    )
    db_session.add(first)
    db_session.commit()

    second = PosInventoryItem(
        product_id=product.id,
        name="Second item",
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_balance_branch_item_pair_is_unique(db_session):
    branch = _create_branch(db_session, "balance-unique")
    item = _create_item(db_session, "balance-unique")

    first = PosInventoryBalance(
        branch_id=branch.id,
        inventory_item_id=item.id,
    )
    db_session.add(first)
    db_session.commit()

    second = PosInventoryBalance(
        branch_id=branch.id,
        inventory_item_id=item.id,
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_balance_rejects_negative_low_stock_threshold(
    db_session,
):
    branch = _create_branch(db_session, "negative-threshold")
    item = _create_item(db_session, "negative-threshold")

    balance = PosInventoryBalance(
        branch_id=branch.id,
        inventory_item_id=item.id,
        low_stock_threshold=Decimal("-0.001"),
    )
    db_session.add(balance)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_balance_allows_negative_quantity_on_hand(
    db_session,
):
    branch = _create_branch(db_session, "negative-stock")
    item = _create_item(db_session, "negative-stock")

    balance = PosInventoryBalance(
        branch_id=branch.id,
        inventory_item_id=item.id,
        quantity_on_hand=Decimal("-3.125"),
    )
    db_session.add(balance)
    db_session.commit()
    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal("-3.125")


def test_inventory_movement_preserves_decimal_values(
    db_session,
):
    branch = _create_branch(db_session, "decimal-movement")
    item = _create_item(db_session, "decimal-movement")

    movement = PosInventoryMovement(
        branch_id=branch.id,
        inventory_item_id=item.id,
        movement_type="ADJUSTMENT",
        quantity_delta=Decimal("-1.125"),
        balance_after=Decimal("7.875"),
    )
    db_session.add(movement)
    db_session.commit()
    db_session.refresh(movement)

    assert movement.quantity_delta == Decimal("-1.125")
    assert movement.balance_after == Decimal("7.875")


def test_inventory_movement_idempotency_key_is_unique_when_present(
    db_session,
):
    branch = _create_branch(db_session, "movement-idempotency")
    item = _create_item(db_session, "movement-idempotency")

    first = PosInventoryMovement(
        branch_id=branch.id,
        inventory_item_id=item.id,
        movement_type="RECEIPT",
        quantity_delta=Decimal("5.000"),
        balance_after=Decimal("5.000"),
        idempotency_key="receipt:test:001",
    )
    db_session.add(first)
    db_session.commit()

    second = PosInventoryMovement(
        branch_id=branch.id,
        inventory_item_id=item.id,
        movement_type="RECEIPT",
        quantity_delta=Decimal("5.000"),
        balance_after=Decimal("10.000"),
        idempotency_key="receipt:test:001",
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()
