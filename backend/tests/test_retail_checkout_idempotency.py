from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.pos_cash import PosCashLedgerEntry
from app.models.pos_staff import PosStaff
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)
from app.models.retail_sales import (
    RetailPayment,
    RetailSale,
)
from app.schemas.retail_sales import (
    RetailCheckoutLineInput,
    RetailCheckoutRequest,
)
from app.services.pos_cash_service import (
    PosCashService,
)
from app.services.retail_sale_service import (
    RetailSaleService,
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


def _staff(
    db_session,
    *,
    branch: Branch,
    name: str,
    role: str = "CASHIER",
) -> PosStaff:
    staff = PosStaff(
        branch_id=branch.id,
        module_code="PAPELERIA",
        display_name=name,
        role=role,
        pin_hash=f"hash-{name}",
        is_active=True,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _product(
    db_session,
    *,
    branch: Branch,
    sku: str,
) -> tuple[
    RetailCatalogItem,
    RetailPresentation,
    RetailInventoryBalance,
]:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=f"Product {sku}",
        category="Idempotency",
        base_unit_code="PIECE",
        cost=Decimal("4.00"),
        inventory_tracked=True,
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("500.000"),
        is_active=True,
    )
    db_session.add(item)
    db_session.flush()

    presentation = RetailPresentation(
        item_id=item.id,
        branch_id=branch.id,
        name="Pieza",
        barcode=f"BAR-{sku}",
        conversion_factor=Decimal("1.000"),
        sale_price=Decimal("10.00"),
        bulk_price=None,
        bulk_min_quantity=None,
        is_default=True,
        is_active=True,
    )
    db_session.add(presentation)
    db_session.flush()

    balance = RetailInventoryBalance(
        branch_id=branch.id,
        item_id=item.id,
        quantity_on_hand=Decimal("100.000"),
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("500.000"),
    )
    db_session.add(balance)
    db_session.commit()

    db_session.refresh(item)
    db_session.refresh(presentation)
    db_session.refresh(balance)

    return item, presentation, balance


def _request(
    *,
    sale_uuid: str,
    payment_uuid: str,
    item: RetailCatalogItem,
    presentation: RetailPresentation,
    method: str,
) -> RetailCheckoutRequest:
    return RetailCheckoutRequest(
        sale_uuid=sale_uuid,
        held_sale_uuid=None,
        lines=[
            RetailCheckoutLineInput(
                item_id=item.id,
                presentation_id=presentation.id,
                quantity=Decimal("2.000"),
                discount_amount=Decimal("0.00"),
            )
        ],
        sale_discount_amount=Decimal("0.00"),
        payment_uuid=payment_uuid,
        payment_method=method,
        amount_tendered=(
            Decimal("20.00")
            if method == "CASH"
            else None
        ),
        external_reference=(
            "CARD-REF"
            if method == "CARD"
            else None
        ),
    )


def _open_shift(
    db_session,
    *,
    branch: Branch,
    cashier: PosStaff,
    terminal_id: str,
):
    manager = _staff(
        db_session,
        branch=branch,
        name=f"Manager {terminal_id}",
        role="MANAGER",
    )

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=terminal_id,
        opening_counts=None,
        opening_amount=Decimal("0.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
        module_code="PAPELERIA",
    )
    db_session.commit()
    db_session.refresh(shift)
    return shift


def test_duplicate_sale_uuid_returns_same_paid_sale_without_double_stock(
    db_session,
):
    branch = _branch(
        db_session,
        "idem-sale",
    )
    cashier = _staff(
        db_session,
        branch=branch,
        name="Idem Cashier",
    )
    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="IDEM-SALE",
    )

    payload = _request(
        sale_uuid="idem-sale-001",
        payment_uuid="idem-payment-001",
        item=item,
        presentation=presentation,
        method="CARD",
    )

    first = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-IDEM",
        manager=None,
    )
    db_session.commit()

    second = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-IDEM",
        manager=None,
    )
    db_session.commit()

    db_session.refresh(balance)

    assert second.id == first.id
    assert second.sale_uuid == first.sale_uuid
    assert second.status == "PAID"

    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )

    assert (
        db_session.query(RetailSale).count()
        == 1
    )
    assert (
        db_session.query(RetailPayment).count()
        == 1
    )
    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 1
    )


def test_duplicate_payment_uuid_does_not_duplicate_payment(
    db_session,
):
    branch = _branch(
        db_session,
        "idem-payment",
    )
    cashier = _staff(
        db_session,
        branch=branch,
        name="Payment Cashier",
    )
    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="IDEM-PAYMENT",
    )

    first_payload = _request(
        sale_uuid="payment-sale-a",
        payment_uuid="shared-payment-uuid",
        item=item,
        presentation=presentation,
        method="CARD",
    )

    RetailSaleService.checkout(
        db_session,
        payload=first_payload,
        staff=cashier,
        terminal_id="PAP-PAY",
        manager=None,
    )
    db_session.commit()

    second_payload = _request(
        sale_uuid="payment-sale-b",
        payment_uuid="shared-payment-uuid",
        item=item,
        presentation=presentation,
        method="CARD",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.checkout(
            db_session,
            payload=second_payload,
            staff=cashier,
            terminal_id="PAP-PAY",
            manager=None,
        )

    assert exc.value.status_code == 409

    db_session.rollback()
    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )

    assert (
        db_session.query(RetailSale).count()
        == 1
    )
    assert (
        db_session.query(RetailPayment).count()
        == 1
    )
    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 1
    )


def test_checkout_retry_does_not_duplicate_cash_ledger(
    db_session,
):
    branch = _branch(
        db_session,
        "idem-ledger",
    )
    cashier = _staff(
        db_session,
        branch=branch,
        name="Ledger Cashier",
    )
    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="IDEM-LEDGER",
    )

    shift = _open_shift(
        db_session,
        branch=branch,
        cashier=cashier,
        terminal_id="PAP-CASH-IDEM",
    )

    payload = _request(
        sale_uuid="cash-retry-sale",
        payment_uuid="cash-retry-payment",
        item=item,
        presentation=presentation,
        method="CASH",
    )

    first = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-CASH-IDEM",
        manager=None,
    )
    db_session.commit()

    second = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-CASH-IDEM",
        manager=None,
    )
    db_session.commit()

    db_session.refresh(balance)

    assert second.id == first.id
    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )

    ledger_rows = (
        db_session.query(
            PosCashLedgerEntry
        )
        .filter(
            PosCashLedgerEntry.shift_id
            == shift.id
        )
        .all()
    )

    assert len(ledger_rows) == 1
    assert (
        ledger_rows[0].idempotency_key
        == "retail-sale:cash-retry-sale"
    )

    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 1
    )
    assert (
        db_session.query(
            RetailPayment
        ).count()
        == 1
    )
