from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)
from app.services.retail_inventory_service import (
    RetailInventoryService,
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
    tracked: bool = True,
) -> tuple[
    RetailCatalogItem,
    RetailPresentation,
]:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=sku,
        category="Test",
        base_unit_code="PIECE",
        cost=Decimal("1.00"),
        inventory_tracked=tracked,
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("100.000"),
        is_active=True,
    )
    db_session.add(item)
    db_session.flush()

    presentation = RetailPresentation(
        item_id=item.id,
        branch_id=branch.id,
        name="Caja 12",
        barcode=f"BOX-{sku}",
        conversion_factor=Decimal("12.000"),
        sale_price=Decimal("100.00"),
        is_default=True,
        is_active=True,
    )

    db_session.add(presentation)
    db_session.commit()
    db_session.refresh(item)
    db_session.refresh(presentation)

    return item, presentation


def _service_item(
    db_session,
    *,
    branch: Branch,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="SERVICE",
        sku="COPY-SERVICE",
        name="Copia B/N",
        category="Copias",
        base_unit_code="SERVICE",
        cost=Decimal("0.00"),
        inventory_tracked=False,
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def _balance(
    db_session,
    *,
    branch: Branch,
    item: RetailCatalogItem,
    quantity: str,
    threshold: str = "5.000",
) -> RetailInventoryBalance:
    balance = RetailInventoryBalance(
        branch_id=branch.id,
        item_id=item.id,
        quantity_on_hand=Decimal(quantity),
        low_stock_threshold=Decimal(threshold),
        max_stock=Decimal("100.000"),
    )
    db_session.add(balance)
    db_session.commit()
    db_session.refresh(balance)
    return balance


def test_initial_movement_sets_balance_and_history(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-initial",
    )
    item, _ = _product(
        db_session,
        branch=branch,
        sku="INITIAL-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="0.000",
    )

    movement = RetailInventoryService.apply_movement(
        db_session,
        balance=balance,
        movement_type="INITIAL",
        quantity_delta=Decimal("25.000"),
        idempotency_key="initial:1",
    )

    db_session.commit()
    db_session.refresh(balance)

    assert movement.quantity_delta == Decimal("25.000")
    assert movement.balance_after == Decimal("25.000")
    assert balance.quantity_on_hand == Decimal("25.000")


def test_manual_entry_and_removal_append_history(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-manual",
    )
    item, _ = _product(
        db_session,
        branch=branch,
        sku="MANUAL-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="10.000",
    )

    entry = RetailInventoryService.apply_movement(
        db_session,
        balance=balance,
        movement_type="MANUAL_ENTRY",
        quantity_delta=Decimal("5.000"),
        idempotency_key="entry:1",
        note="Compra local",
    )

    removal = RetailInventoryService.apply_movement(
        db_session,
        balance=balance,
        movement_type="MANUAL_REMOVAL",
        quantity_delta=Decimal("-2.000"),
        idempotency_key="removal:1",
        note="Merma",
    )

    db_session.commit()
    db_session.refresh(balance)

    assert entry.balance_after == Decimal("15.000")
    assert removal.balance_after == Decimal("13.000")
    assert balance.quantity_on_hand == Decimal("13.000")

    rows = (
        db_session.execute(
            select(RetailInventoryMovement)
            .where(
                RetailInventoryMovement.item_id
                == item.id
            )
            .order_by(
                RetailInventoryMovement.id
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 2
    assert rows[0].id == entry.id
    assert rows[1].id == removal.id
    assert rows[0].quantity_delta == Decimal("5.000")


def test_adjustment_to_physical_count_uses_delta(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-adjust",
    )
    item, _ = _product(
        db_session,
        branch=branch,
        sku="ADJUST-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="18.000",
    )

    movement = (
        RetailInventoryService.adjust_to_physical_count(
            db_session,
            balance=balance,
            physical_quantity=Decimal("14.500"),
            idempotency_key="adjust:1",
            note="Conteo físico",
        )
    )

    db_session.commit()
    db_session.refresh(balance)

    assert movement.movement_type == "ADJUSTMENT"
    assert movement.quantity_delta == Decimal("-3.500")
    assert movement.balance_after == Decimal("14.500")
    assert balance.quantity_on_hand == Decimal("14.500")


def test_low_stock_status_is_deterministic(
    db_session,
):
    assert (
        RetailInventoryService.status_for(
            quantity_on_hand=Decimal("0.000"),
            low_stock_threshold=Decimal("5.000"),
        )
        == "OUT_OF_STOCK"
    )

    assert (
        RetailInventoryService.status_for(
            quantity_on_hand=Decimal("5.000"),
            low_stock_threshold=Decimal("5.000"),
        )
        == "LOW_STOCK"
    )

    assert (
        RetailInventoryService.status_for(
            quantity_on_hand=Decimal("5.001"),
            low_stock_threshold=Decimal("5.000"),
        )
        == "AVAILABLE"
    )


def test_service_item_does_not_create_inventory_movement(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-service",
    )
    item = _service_item(
        db_session,
        branch=branch,
    )

    movement = RetailInventoryService.decrement_for_sale(
        db_session,
        item=item,
        presentation=None,
        quantity=Decimal("10.000"),
        sale_id=100,
        sale_line_id=200,
        idempotency_key="service-sale:1",
    )

    assert movement is None

    count = db_session.query(
        RetailInventoryMovement
    ).count()

    assert count == 0


def test_untracked_product_does_not_create_inventory_movement(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-untracked",
    )
    item, presentation = _product(
        db_session,
        branch=branch,
        sku="UNTRACKED-001",
        tracked=False,
    )

    movement = RetailInventoryService.decrement_for_sale(
        db_session,
        item=item,
        presentation=presentation,
        quantity=Decimal("2.000"),
        sale_id=101,
        sale_line_id=201,
        idempotency_key="untracked-sale:1",
    )

    assert movement is None


def test_two_boxes_of_twelve_decrement_exactly_24_base_units(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-box-conversion",
    )
    item, presentation = _product(
        db_session,
        branch=branch,
        sku="BOX-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="30.000",
    )

    movement = RetailInventoryService.decrement_for_sale(
        db_session,
        item=item,
        presentation=presentation,
        quantity=Decimal("2.000"),
        sale_id=102,
        sale_line_id=202,
        idempotency_key="box-sale:1",
    )

    db_session.commit()
    db_session.refresh(balance)

    assert movement is not None
    assert movement.quantity_delta == Decimal("-24.000")
    assert movement.balance_after == Decimal("6.000")
    assert balance.quantity_on_hand == Decimal("6.000")


def test_duplicate_idempotency_key_does_not_double_apply(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-idempotent",
    )
    item, _ = _product(
        db_session,
        branch=branch,
        sku="IDEMPOTENT-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="10.000",
    )

    first = RetailInventoryService.apply_movement(
        db_session,
        balance=balance,
        movement_type="MANUAL_ENTRY",
        quantity_delta=Decimal("5.000"),
        idempotency_key="same-movement-key",
    )

    second = RetailInventoryService.apply_movement(
        db_session,
        balance=balance,
        movement_type="MANUAL_ENTRY",
        quantity_delta=Decimal("5.000"),
        idempotency_key="same-movement-key",
    )

    db_session.commit()
    db_session.refresh(balance)

    assert first.id == second.id
    assert balance.quantity_on_hand == Decimal("15.000")

    count = db_session.query(
        RetailInventoryMovement
    ).filter(
        RetailInventoryMovement.idempotency_key
        == "same-movement-key"
    ).count()

    assert count == 1


def test_sale_cannot_drive_stock_below_zero(
    db_session,
):
    branch = _branch(
        db_session,
        "inventory-insufficient",
    )
    item, presentation = _product(
        db_session,
        branch=branch,
        sku="LOW-001",
    )
    balance = _balance(
        db_session,
        branch=branch,
        item=item,
        quantity="10.000",
    )

    with pytest.raises(HTTPException) as exc:
        RetailInventoryService.decrement_for_sale(
            db_session,
            item=item,
            presentation=presentation,
            quantity=Decimal("1.000"),
            sale_id=103,
            sale_line_id=203,
            idempotency_key="insufficient:1",
        )

    assert exc.value.status_code == 409

    db_session.refresh(balance)
    assert balance.quantity_on_hand == Decimal("10.000")
