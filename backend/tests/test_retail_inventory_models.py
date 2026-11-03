from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.branch import Branch
from app.models.retail_catalog import RetailCatalogItem
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)


def _branch(db_session, code: str) -> Branch:
    branch = Branch(
        name=f"Branch {code}",
        code=code,
        is_active=True,
    )
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    return branch


def _product(
    db_session,
    *,
    branch: Branch,
    sku: str,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=sku,
        category="Test",
        base_unit_code="PIECE",
        cost=Decimal("1.00"),
        inventory_tracked=True,
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("100.000"),
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_inventory_balance_persists_decimal_quantities(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-model-balance",
    )
    item = _product(
        db_session,
        branch=branch,
        sku="INV-001",
    )

    balance = RetailInventoryBalance(
        branch_id=branch.id,
        item_id=item.id,
        quantity_on_hand=Decimal("12.375"),
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("100.000"),
    )

    db_session.add(balance)
    db_session.commit()
    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal("12.375")
    assert balance.low_stock_threshold == Decimal("5.000")
    assert balance.max_stock == Decimal("100.000")


def test_inventory_balance_is_unique_per_branch_item(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-model-unique",
    )
    item = _product(
        db_session,
        branch=branch,
        sku="INV-002",
    )

    db_session.add(
        RetailInventoryBalance(
            branch_id=branch.id,
            item_id=item.id,
            quantity_on_hand=Decimal("0.000"),
            low_stock_threshold=Decimal("5.000"),
            max_stock=None,
        )
    )
    db_session.commit()

    db_session.add(
        RetailInventoryBalance(
            branch_id=branch.id,
            item_id=item.id,
            quantity_on_hand=Decimal("1.000"),
            low_stock_threshold=Decimal("5.000"),
            max_stock=None,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    "movement_type",
    [
        "INITIAL",
        "MANUAL_ENTRY",
        "MANUAL_REMOVAL",
        "ADJUSTMENT",
        "SALE",
        "RETURN",
        "CANCELLATION_REVERSAL",
    ],
)
def test_inventory_movement_accepts_defined_types(
    db_session,
    movement_type,
):
    branch = _branch(
        db_session,
        f"movement-{movement_type.lower()}",
    )
    item = _product(
        db_session,
        branch=branch,
        sku=f"SKU-{movement_type}",
    )

    balance = RetailInventoryBalance(
        branch_id=branch.id,
        item_id=item.id,
        quantity_on_hand=Decimal("10.000"),
        low_stock_threshold=Decimal("2.000"),
        max_stock=None,
    )
    db_session.add(balance)
    db_session.flush()

    movement = RetailInventoryMovement(
        branch_id=branch.id,
        item_id=item.id,
        movement_type=movement_type,
        quantity_delta=Decimal("1.000"),
        balance_after=Decimal("11.000"),
        idempotency_key=(
            f"model:{movement_type}:{item.id}"
        ),
    )

    db_session.add(movement)
    db_session.commit()

    assert movement.id is not None
    assert movement.movement_type == movement_type


def test_inventory_movement_rejects_unknown_type(
    db_session,
):
    branch = _branch(
        db_session,
        "movement-invalid",
    )
    item = _product(
        db_session,
        branch=branch,
        sku="INV-INVALID",
    )

    movement = RetailInventoryMovement(
        branch_id=branch.id,
        item_id=item.id,
        movement_type="DELETE_HISTORY",
        quantity_delta=Decimal("1.000"),
        balance_after=Decimal("1.000"),
        idempotency_key="invalid-type",
    )

    db_session.add(movement)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_inventory_idempotency_key_is_unique(
    db_session,
):
    branch = _branch(
        db_session,
        "movement-idempotency",
    )
    item = _product(
        db_session,
        branch=branch,
        sku="INV-IDEMPOTENT",
    )

    for index in range(2):
        movement = RetailInventoryMovement(
            branch_id=branch.id,
            item_id=item.id,
            movement_type="MANUAL_ENTRY",
            quantity_delta=Decimal("1.000"),
            balance_after=Decimal(
                f"{index + 1}.000"
            ),
            idempotency_key="same-key",
        )

        db_session.add(movement)

        if index == 0:
            db_session.commit()
        else:
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()
