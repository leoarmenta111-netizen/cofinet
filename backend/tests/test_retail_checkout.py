from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.branch import Branch
from app.models.pos_cash import (
    PosCashLedgerEntry,
)
from app.models.pos_audit import PosAuditEvent
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
    RetailHeldSaleLineInput,
    RetailHeldSaleUpsert,
)
from app.services.pos_cash_service import (
    PosCashService,
)
from app.services.retail_sale_service import (
    RetailSaleService,
)


def _branch(
    db_session,
    code: str,
) -> Branch:
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
    module_code: str = "PAPELERIA",
) -> PosStaff:
    staff = PosStaff(
        branch_id=branch.id,
        module_code=module_code,
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
    sale_price: str = "10.00",
    conversion_factor: str = "1.000",
    stock: str = "100.000",
    inventory_tracked: bool = True,
) -> tuple[
    RetailCatalogItem,
    RetailPresentation,
    RetailInventoryBalance | None,
]:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=f"Product {sku}",
        category="Checkout",
        base_unit_code="PIECE",
        cost=Decimal("4.00"),
        inventory_tracked=inventory_tracked,
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("500.000"),
        is_active=True,
    )

    db_session.add(item)
    db_session.flush()

    presentation = RetailPresentation(
        item_id=item.id,
        branch_id=branch.id,
        name="Presentación",
        barcode=f"BAR-{sku}",
        conversion_factor=Decimal(
            conversion_factor
        ),
        sale_price=Decimal(sale_price),
        bulk_price=None,
        bulk_min_quantity=None,
        is_default=True,
        is_active=True,
    )

    db_session.add(presentation)
    db_session.flush()

    balance = None

    if inventory_tracked:
        balance = RetailInventoryBalance(
            branch_id=branch.id,
            item_id=item.id,
            quantity_on_hand=Decimal(stock),
            low_stock_threshold=Decimal(
                "5.000"
            ),
            max_stock=Decimal("500.000"),
        )
        db_session.add(balance)

    db_session.commit()

    db_session.refresh(item)
    db_session.refresh(presentation)

    if balance is not None:
        db_session.refresh(balance)

    return item, presentation, balance


def _open_shift(
    db_session,
    *,
    branch: Branch,
    terminal_id: str,
    module_code: str = "PAPELERIA",
):
    cashier = _staff(
        db_session,
        branch=branch,
        name=(
            f"{module_code} Shift Cashier "
            f"{terminal_id}"
        ),
        module_code=module_code,
    )

    manager = _staff(
        db_session,
        branch=branch,
        name=(
            f"{module_code} Shift Manager "
            f"{terminal_id}"
        ),
        role="MANAGER",
        module_code=module_code,
    )

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=terminal_id,
        opening_counts=None,
        opening_amount=Decimal("0.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
        module_code=module_code,
    )

    db_session.commit()
    db_session.refresh(shift)

    return shift


def _request(
    *,
    sale_uuid: str,
    payment_uuid: str,
    item: RetailCatalogItem,
    presentation: RetailPresentation,
    quantity: str,
    payment_method: str,
    amount_tendered: str | None = None,
    external_reference: str | None = None,
    sale_discount_amount: str = "0.00",
) -> RetailCheckoutRequest:
    return RetailCheckoutRequest(
        sale_uuid=sale_uuid,
        held_sale_uuid=None,
        lines=[
            RetailCheckoutLineInput(
                item_id=item.id,
                presentation_id=(
                    presentation.id
                ),
                quantity=Decimal(quantity),
                discount_amount=Decimal(
                    "0.00"
                ),
            )
        ],
        sale_discount_amount=Decimal(
            sale_discount_amount
        ),
        payment_uuid=payment_uuid,
        payment_method=payment_method,
        amount_tendered=(
            Decimal(amount_tendered)
            if amount_tendered is not None
            else None
        ),
        external_reference=(
            external_reference
        ),
    )


def test_cash_checkout_exact_tender(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-cash-exact",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cash Exact",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="CASH-EXACT",
    )

    shift = _open_shift(
        db_session,
        branch=branch,
        terminal_id="PAP-T1",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_request(
            sale_uuid="sale-cash-exact",
            payment_uuid="pay-cash-exact",
            item=item,
            presentation=presentation,
            quantity="2.000",
            payment_method="CASH",
            amount_tendered="20.00",
        ),
        staff=cashier,
        terminal_id="PAP-T1",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(sale)
    db_session.refresh(balance)

    assert sale.status == "PAID"
    assert sale.subtotal == Decimal("20.00")
    assert sale.discount_total == Decimal(
        "0.00"
    )
    assert sale.total == Decimal("20.00")

    assert len(sale.payments) == 1

    payment = sale.payments[0]

    assert payment.method == "CASH"
    assert payment.amount == Decimal("20.00")
    assert payment.amount_tendered == Decimal(
        "20.00"
    )
    assert payment.change_due == Decimal(
        "0.00"
    )

    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )

    movements = (
        db_session.query(
            RetailInventoryMovement
        ).all()
    )

    assert len(movements) == 1
    assert movements[0].movement_type == "SALE"
    assert movements[0].quantity_delta == Decimal(
        "-2.000"
    )

    ledgers = (
        db_session.query(
            PosCashLedgerEntry
        ).all()
    )

    assert len(ledgers) == 1

    ledger = ledgers[0]

    assert ledger.shift_id == shift.id
    assert ledger.entry_type == "RETAIL_SALE"
    assert ledger.amount == Decimal("20.00")
    assert (
        ledger.idempotency_key
        == "retail-sale:sale-cash-exact"
    )
    assert ledger.reference_type == (
        "retail_sale"
    )
    assert ledger.reference_id == (
        "sale-cash-exact"
    )


def test_cash_checkout_calculates_change(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-change",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cash Change",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="CASH-CHANGE",
    )

    _open_shift(
        db_session,
        branch=branch,
        terminal_id="PAP-T2",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_request(
            sale_uuid="sale-change",
            payment_uuid="pay-change",
            item=item,
            presentation=presentation,
            quantity="2.000",
            payment_method="CASH",
            amount_tendered="50.00",
        ),
        staff=cashier,
        terminal_id="PAP-T2",
        manager=None,
    )

    db_session.commit()

    payment = sale.payments[0]

    assert payment.amount == Decimal("20.00")
    assert payment.amount_tendered == Decimal(
        "50.00"
    )
    assert payment.change_due == Decimal(
        "30.00"
    )


def test_card_checkout_records_reference_without_cash_ledger(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-card",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Card Cashier",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="CARD-001",
        sale_price="25.00",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_request(
            sale_uuid="sale-card",
            payment_uuid="pay-card",
            item=item,
            presentation=presentation,
            quantity="2.000",
            payment_method="CARD",
            external_reference=(
                "TERMINAL-AUTH-123"
            ),
        ),
        staff=cashier,
        terminal_id="PAP-CARD",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(balance)

    payment = sale.payments[0]

    assert sale.status == "PAID"
    assert sale.total == Decimal("50.00")
    assert payment.method == "CARD"
    assert payment.amount == Decimal("50.00")
    assert payment.amount_tendered is None
    assert payment.change_due == Decimal(
        "0.00"
    )
    assert (
        payment.external_reference
        == "TERMINAL-AUTH-123"
    )

    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )

    assert (
        db_session.query(
            PosCashLedgerEntry
        ).count()
        == 0
    )


def test_product_checkout_uses_presentation_conversion(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-conversion",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Conversion Cashier",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="BOX-12",
        sale_price="35.00",
        conversion_factor="12.000",
        stock="100.000",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_request(
            sale_uuid="sale-boxes",
            payment_uuid="pay-boxes",
            item=item,
            presentation=presentation,
            quantity="2.000",
            payment_method="CARD",
            external_reference="CARD-BOX",
        ),
        staff=cashier,
        terminal_id="PAP-T3",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(balance)

    assert sale.total == Decimal("70.00")
    assert balance.quantity_on_hand == Decimal(
        "76.000"
    )

    movement = (
        db_session.query(
            RetailInventoryMovement
        ).one()
    )

    assert movement.quantity_delta == Decimal(
        "-24.000"
    )
    assert movement.balance_after == Decimal(
        "76.000"
    )


def test_cash_checkout_requires_open_papeleria_shift(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-no-shift",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="No Shift Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="NO-SHIFT",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.checkout(
            db_session,
            payload=_request(
                sale_uuid="sale-no-shift",
                payment_uuid="pay-no-shift",
                item=item,
                presentation=presentation,
                quantity="1.000",
                payment_method="CASH",
                amount_tendered="10.00",
            ),
            staff=cashier,
            terminal_id="PAP-NO-SHIFT",
            manager=None,
        )

    assert exc.value.status_code == 409

    db_session.rollback()

    assert (
        db_session.query(RetailSale).count()
        == 0
    )
    assert (
        db_session.query(RetailPayment).count()
        == 0
    )
    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 0
    )
    assert (
        db_session.query(
            PosCashLedgerEntry
        ).count()
        == 0
    )


def test_cafe_shift_does_not_satisfy_papeleria_checkout(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-cafe-shift",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Papeleria Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="CAFE-SHIFT",
    )

    _open_shift(
        db_session,
        branch=branch,
        terminal_id="SHARED-T1",
        module_code="CAFE",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.checkout(
            db_session,
            payload=_request(
                sale_uuid="sale-cafe-shift",
                payment_uuid="pay-cafe-shift",
                item=item,
                presentation=presentation,
                quantity="1.000",
                payment_method="CASH",
                amount_tendered="10.00",
            ),
            staff=cashier,
            terminal_id="SHARED-T1",
            manager=None,
        )

    assert exc.value.status_code == 409

    db_session.rollback()


def test_insufficient_stock_rolls_back_sale_effects(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-stock",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Stock Cashier",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="LOW-STOCK",
        stock="5.000",
    )

    _open_shift(
        db_session,
        branch=branch,
        terminal_id="PAP-STOCK",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.checkout(
            db_session,
            payload=_request(
                sale_uuid="sale-low-stock",
                payment_uuid="pay-low-stock",
                item=item,
                presentation=presentation,
                quantity="10.000",
                payment_method="CASH",
                amount_tendered="100.00",
            ),
            staff=cashier,
            terminal_id="PAP-STOCK",
            manager=None,
        )

    assert exc.value.status_code == 409

    db_session.rollback()
    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal(
        "5.000"
    )

    assert (
        db_session.query(RetailSale).count()
        == 0
    )
    assert (
        db_session.query(RetailPayment).count()
        == 0
    )
    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 0
    )
    assert (
        db_session.query(
            PosCashLedgerEntry
        ).count()
        == 0
    )


def test_sale_discount_requires_manager(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-discount-no-manager",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Discount Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="DISC-NO-MGR",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.checkout(
            db_session,
            payload=_request(
                sale_uuid="sale-disc-no-mgr",
                payment_uuid="pay-disc-no-mgr",
                item=item,
                presentation=presentation,
                quantity="2.000",
                payment_method="CARD",
                external_reference="CARD-DISC",
                sale_discount_amount="5.00",
            ),
            staff=cashier,
            terminal_id="PAP-DISC",
            manager=None,
        )

    assert exc.value.status_code == 403

    db_session.rollback()


def test_sale_discount_with_manager_is_applied_server_side(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-discount-manager",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Discount Cashier",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Discount Manager",
        role="MANAGER",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="DISC-MGR",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_request(
            sale_uuid="sale-disc-manager",
            payment_uuid="pay-disc-manager",
            item=item,
            presentation=presentation,
            quantity="2.000",
            payment_method="CARD",
            external_reference="CARD-DISC-MGR",
            sale_discount_amount="5.00",
        ),
        staff=cashier,
        terminal_id="PAP-DISC",
        manager=manager,
    )

    db_session.commit()

    assert sale.subtotal == Decimal("20.00")
    assert sale.discount_total == Decimal(
        "5.00"
    )
    assert sale.total == Decimal("15.00")

    assert sale.payments[0].amount == Decimal(
        "15.00"
    )


def test_client_supplied_price_is_rejected_by_schema():
    with pytest.raises(ValidationError):
        RetailCheckoutLineInput.model_validate(
            {
                "item_id": 123,
                "presentation_id": 456,
                "quantity": "1.000",
                "discount_amount": "0.00",
                "unit_price": "0.01",
            }
        )


from app.auth.pos_staff_security import (
    get_current_pos_staff,
)
from app.auth.security import (
    get_current_token,
    hash_password,
)
from app.main import app
from app.models.retail_catalog import (
    RetailServicePriceTier,
)


def _service_item(
    db_session,
    *,
    branch: Branch,
    sku: str,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="SERVICE",
        sku=sku,
        name=f"Service {sku}",
        category="Copias",
        base_unit_code="PIECE",
        cost=Decimal("0.50"),
        inventory_tracked=False,
        low_stock_threshold=None,
        max_stock=None,
        is_active=True,
    )

    db_session.add(item)
    db_session.flush()

    db_session.add_all(
        [
            RetailServicePriceTier(
                item_id=item.id,
                min_quantity=Decimal("1.000"),
                max_quantity=Decimal("20.000"),
                unit_price=Decimal("2.00"),
            ),
            RetailServicePriceTier(
                item_id=item.id,
                min_quantity=Decimal("21.000"),
                max_quantity=Decimal("100.000"),
                unit_price=Decimal("1.50"),
            ),
            RetailServicePriceTier(
                item_id=item.id,
                min_quantity=Decimal("101.000"),
                max_quantity=None,
                unit_price=Decimal("1.00"),
            ),
        ]
    )

    db_session.commit()
    db_session.refresh(item)

    return item


def _manager_with_real_pin(
    db_session,
    *,
    branch: Branch,
    name: str,
    pin: str,
    module_code: str = "PAPELERIA",
) -> PosStaff:
    manager = PosStaff(
        branch_id=branch.id,
        module_code=module_code,
        display_name=name,
        role="MANAGER",
        pin_hash=hash_password(pin),
        is_active=True,
    )

    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)

    return manager


def _checkout_api_request(
    *,
    client,
    staff,
    branch,
    terminal_id,
    payload,
):
    def current_staff_override():
        return staff

    def token_override():
        return {
            "branch_code": branch.code,
            "terminal_id": terminal_id,
        }

    app.dependency_overrides[
        get_current_pos_staff
    ] = current_staff_override

    app.dependency_overrides[
        get_current_token
    ] = token_override

    try:
        return client.post(
            "/retail/sales/checkout",
            json=payload,
        )
    finally:
        app.dependency_overrides.pop(
            get_current_pos_staff,
            None,
        )
        app.dependency_overrides.pop(
            get_current_token,
            None,
        )


def test_service_checkout_uses_tier_price_without_inventory(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-service-tier",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Service Cashier",
    )

    item = _service_item(
        db_session,
        branch=branch,
        sku="COPY-BW",
    )

    payload = RetailCheckoutRequest(
        sale_uuid="service-tier-sale",
        held_sale_uuid=None,
        lines=[
            RetailCheckoutLineInput(
                item_id=item.id,
                presentation_id=None,
                quantity=Decimal("21.000"),
                discount_amount=Decimal("0.00"),
            )
        ],
        sale_discount_amount=Decimal("0.00"),
        payment_uuid="service-tier-payment",
        payment_method="CARD",
        amount_tendered=None,
        external_reference="CARD-COPIES",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-SERVICE",
        manager=None,
    )

    db_session.commit()

    assert sale.status == "PAID"
    assert sale.subtotal == Decimal("31.50")
    assert sale.total == Decimal("31.50")

    assert len(sale.lines) == 1
    assert sale.lines[0].item_type == "SERVICE"
    assert sale.lines[0].unit_price == Decimal("1.50")
    assert sale.lines[0].quantity == Decimal("21.000")
    assert sale.lines[0].line_total == Decimal("31.50")

    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 0
    )

    assert (
        db_session.query(
            RetailInventoryBalance
        )
        .filter(
            RetailInventoryBalance.item_id
            == item.id
        )
        .count()
        == 0
    )


def test_held_sale_is_repriced_at_checkout(
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-held-reprice",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Held Reprice Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-REPRICE",
        sale_price="10.00",
    )

    held = RetailSaleService.hold(
        db_session,
        payload=RetailHeldSaleUpsert(
            label="Precio viejo",
            lines=[
                RetailHeldSaleLineInput(
                    item_id=item.id,
                    presentation_id=presentation.id,
                    quantity=Decimal("2.000"),
                )
            ],
        ),
        staff=cashier,
        terminal_id="PAP-HELD",
    )

    db_session.commit()

    assert held.total == Decimal("20.00")

    presentation.sale_price = Decimal("12.00")
    db_session.commit()

    checkout_payload = RetailCheckoutRequest(
        sale_uuid=held.sale_uuid,
        held_sale_uuid=held.sale_uuid,
        lines=[
            RetailCheckoutLineInput(
                item_id=item.id,
                presentation_id=presentation.id,
                quantity=Decimal("2.000"),
                discount_amount=Decimal("0.00"),
            )
        ],
        sale_discount_amount=Decimal("0.00"),
        payment_uuid="held-final-payment",
        payment_method="CARD",
        amount_tendered=None,
        external_reference="CARD-HELD",
    )

    paid = RetailSaleService.checkout(
        db_session,
        payload=checkout_payload,
        staff=cashier,
        terminal_id="PAP-HELD",
        manager=None,
    )

    db_session.commit()

    assert paid.status == "PAID"
    assert paid.id == held.id
    assert paid.sale_uuid == held.sale_uuid

    remaining_held = (
        RetailSaleService.list_held(
            db_session,
            staff=cashier,
        )
    )

    assert remaining_held == []

    # Held preview was 20.00.
    # Current catalog is authoritative at checkout.
    assert paid.subtotal == Decimal("24.00")
    assert paid.total == Decimal("24.00")
    assert paid.lines[0].unit_price == Decimal("12.00")


def test_http_checkout_card_without_discount(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-http-card",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="HTTP Card Cashier",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="HTTP-CARD",
        sale_price="15.00",
    )

    response = _checkout_api_request(
        client=client,
        staff=cashier,
        branch=branch,
        terminal_id="PAP-HTTP",
        payload={
            "sale_uuid": "http-card-sale",
            "held_sale_uuid": None,
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": presentation.id,
                    "quantity": "2.000",
                    "discount_amount": "0.00",
                }
            ],
            "sale_discount_amount": "0.00",
            "payment_uuid": "http-card-payment",
            "payment_method": "CARD",
            "amount_tendered": None,
            "external_reference": "CARD-HTTP-001",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["sale_uuid"] == "http-card-sale"
    assert body["status"] == "PAID"
    assert body["total"] == "30.00"
    assert body["payments"][0]["method"] == "CARD"

    db_session.refresh(balance)

    assert balance.quantity_on_hand == Decimal(
        "98.000"
    )


def test_http_discount_authorizes_papeleria_manager_pin(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-http-manager",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="HTTP Discount Cashier",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="HTTP Discount Manager",
        pin="2468",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-DISCOUNT",
        sale_price="20.00",
    )

    response = _checkout_api_request(
        client=client,
        staff=cashier,
        branch=branch,
        terminal_id="PAP-DISCOUNT",
        payload={
            "sale_uuid": "http-discount-sale",
            "held_sale_uuid": None,
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": presentation.id,
                    "quantity": "1.000",
                    "discount_amount": "0.00",
                }
            ],
            "sale_discount_amount": "5.00",
            "payment_uuid": "http-discount-payment",
            "payment_method": "CARD",
            "amount_tendered": None,
            "external_reference": "CARD-DISCOUNT",
            "authorizing_manager_staff_id": manager.id,
            "manager_pin": "2468",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["subtotal"] == "20.00"
    assert body["discount_total"] == "5.00"
    assert body["total"] == "15.00"

    events = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type
            == "RETAIL_DISCOUNT_AUTHORIZED"
        )
        .all()
    )

    assert len(events) == 1

    event = events[0]

    assert event.branch_id == branch.id
    assert event.terminal_id == "PAP-DISCOUNT"
    assert event.actor_staff_id == cashier.id
    assert event.authorizer_staff_id == manager.id
    assert event.target_type == "retail_sale"
    assert event.target_id == "http-discount-sale"

    assert (
        event.metadata_json["discount_total"]
        == "5.00"
    )


def test_http_discount_without_manager_credentials_is_rejected(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-http-no-manager",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="HTTP No Manager",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-NO-MANAGER",
    )

    response = _checkout_api_request(
        client=client,
        staff=cashier,
        branch=branch,
        terminal_id="PAP-NO-MANAGER",
        payload={
            "sale_uuid": "http-no-manager-sale",
            "held_sale_uuid": None,
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": presentation.id,
                    "quantity": "1.000",
                    "discount_amount": "0.00",
                }
            ],
            "sale_discount_amount": "2.00",
            "payment_uuid": "http-no-manager-payment",
            "payment_method": "CARD",
            "amount_tendered": None,
            "external_reference": "CARD-NO-MGR",
        },
    )

    assert response.status_code in {
        403,
        422,
    }

    assert (
        db_session.query(RetailSale)
        .filter(
            RetailSale.sale_uuid
            == "http-no-manager-sale"
        )
        .count()
        == 0
    )


def test_http_cafe_manager_cannot_authorize_papeleria_discount(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "checkout-http-cafe-manager",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Papeleria Checkout Cashier",
    )

    cafe_manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="Cafe Manager",
        pin="1357",
        module_code="CAFE",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-CAFE-MGR",
    )

    response = _checkout_api_request(
        client=client,
        staff=cashier,
        branch=branch,
        terminal_id="PAP-CAFE-MGR",
        payload={
            "sale_uuid": "http-cafe-manager-sale",
            "held_sale_uuid": None,
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": presentation.id,
                    "quantity": "1.000",
                    "discount_amount": "0.00",
                }
            ],
            "sale_discount_amount": "2.00",
            "payment_uuid": "http-cafe-manager-payment",
            "payment_method": "CARD",
            "amount_tendered": None,
            "external_reference": "CARD-CAFE-MGR",
            "authorizing_manager_staff_id": cafe_manager.id,
            "manager_pin": "1357",
        },
    )

    assert response.status_code in {
        401,
        403,
    }

    assert (
        db_session.query(RetailSale)
        .filter(
            RetailSale.sale_uuid
            == "http-cafe-manager-sale"
        )
        .count()
        == 0
    )
