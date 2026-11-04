from copy import deepcopy
from decimal import Decimal

from app.auth.pos_staff_security import (
    get_current_pos_staff,
)
from app.auth.security import get_current_token
from app.main import app
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

from test_retail_checkout import (
    _branch,
    _manager_with_real_pin,
    _product,
    _staff,
)


def _card_payload(
    *,
    sale_uuid: str,
    payment_uuid: str,
    item_id: int,
    presentation_id: int,
    quantity: str = "2.000",
    sale_discount: str = "0.00",
) -> RetailCheckoutRequest:
    return RetailCheckoutRequest(
        sale_uuid=sale_uuid,
        held_sale_uuid=None,
        lines=[
            RetailCheckoutLineInput(
                item_id=item_id,
                presentation_id=presentation_id,
                quantity=Decimal(quantity),
                discount_amount=Decimal("0.00"),
            )
        ],
        sale_discount_amount=Decimal(
            sale_discount
        ),
        payment_uuid=payment_uuid,
        payment_method="CARD",
        amount_tendered=None,
        external_reference=(
            f"REF-{payment_uuid}"
        ),
    )


def _get_receipt(
    *,
    client,
    staff,
    branch,
    terminal_id: str,
    sale_uuid: str,
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
        return client.get(
            f"/retail/sales/{sale_uuid}/receipt"
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


def test_card_checkout_freezes_receipt_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-card",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Receipt Card Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="RECEIPT-CARD",
        sale_price="12.50",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_card_payload(
            sale_uuid="receipt-card-sale",
            payment_uuid="receipt-card-payment",
            item_id=item.id,
            presentation_id=presentation.id,
        ),
        staff=cashier,
        terminal_id="PAP-RECEIPT-CARD",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(sale)

    snapshot = sale.receipt_snapshot

    assert isinstance(snapshot, dict)

    assert snapshot["schema_version"] == 1
    assert (
        snapshot["sale_uuid"]
        == "receipt-card-sale"
    )
    assert snapshot["folio"]
    assert snapshot["sold_at"]

    assert (
        snapshot["business"]["module_code"]
        == "PAPELERIA"
    )

    assert snapshot["branch"] == {
        "id": branch.id,
        "code": branch.code,
        "name": branch.name,
    }

    assert (
        snapshot["terminal_id"]
        == "PAP-RECEIPT-CARD"
    )

    assert snapshot["cashier"] == {
        "staff_id": cashier.id,
        "display_name": cashier.display_name,
    }

    assert snapshot["authorizer"] is None

    assert len(snapshot["lines"]) == 1

    line = snapshot["lines"][0]

    assert line["item_id"] == item.id
    assert (
        line["presentation_id"]
        == presentation.id
    )
    assert line["sku"] == "RECEIPT-CARD"
    assert (
        line["quantity"]
        == "2.000"
    )
    assert (
        line["unit_price"]
        == "12.50"
    )
    assert (
        line["line_total"]
        == "25.00"
    )

    assert snapshot["totals"] == {
        "subtotal": "25.00",
        "discount_total": "0.00",
        "total": "25.00",
        "currency": "MXN",
    }

    assert (
        snapshot["payment"]["method"]
        == "CARD"
    )
    assert (
        snapshot["payment"]["amount"]
        == "25.00"
    )
    assert (
        snapshot["payment"][
            "external_reference"
        ]
        == "REF-receipt-card-payment"
    )

    assert "fiscal" not in snapshot


def test_receipt_reprint_uses_stored_snapshot_after_catalog_change(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-immutable",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Immutable Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="IMMUTABLE-001",
        sale_price="18.00",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_card_payload(
            sale_uuid="immutable-sale",
            payment_uuid="immutable-payment",
            item_id=item.id,
            presentation_id=presentation.id,
        ),
        staff=cashier,
        terminal_id="PAP-IMMUTABLE",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(sale)

    frozen = deepcopy(
        sale.receipt_snapshot
    )

    assert frozen is not None

    item.name = "RENAMED AFTER SALE"
    presentation.sale_price = Decimal(
        "999.00"
    )

    db_session.commit()

    response = _get_receipt(
        client=client,
        staff=cashier,
        branch=branch,
        terminal_id="PAP-IMMUTABLE",
        sale_uuid="immutable-sale",
    )

    assert response.status_code == 200
    assert response.json() == frozen

    assert (
        response.json()["lines"][0]["name"]
        != "RENAMED AFTER SALE"
    )

    assert (
        response.json()["lines"][0][
            "unit_price"
        ]
        == "18.00"
    )


def test_cash_receipt_freezes_tendered_and_change(
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-cash",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Receipt Cash Cashier",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="Receipt Cash Manager",
        pin="2468",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="RECEIPT-CASH",
        sale_price="10.00",
    )

    PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id="PAP-RECEIPT-CASH",
        opening_counts=None,
        opening_amount=Decimal("0.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
        module_code="PAPELERIA",
    )

    db_session.commit()

    payload = RetailCheckoutRequest(
        sale_uuid="receipt-cash-sale",
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
        payment_uuid="receipt-cash-payment",
        payment_method="CASH",
        amount_tendered=Decimal("30.00"),
        external_reference=None,
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-RECEIPT-CASH",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(sale)

    payment = (
        sale.receipt_snapshot["payment"]
    )

    assert payment["method"] == "CASH"
    assert payment["amount"] == "20.00"
    assert (
        payment["amount_tendered"]
        == "30.00"
    )
    assert (
        payment["change_due"]
        == "10.00"
    )
    assert (
        payment["external_reference"]
        is None
    )


def test_discount_receipt_freezes_authorizer(
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-discount",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Discount Cashier",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="Discount Manager",
        pin="1357",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="RECEIPT-DISCOUNT",
        sale_price="20.00",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=_card_payload(
            sale_uuid="receipt-discount-sale",
            payment_uuid=(
                "receipt-discount-payment"
            ),
            item_id=item.id,
            presentation_id=presentation.id,
            quantity="1.000",
            sale_discount="5.00",
        ),
        staff=cashier,
        terminal_id="PAP-RECEIPT-DISCOUNT",
        manager=manager,
    )

    db_session.commit()
    db_session.refresh(sale)

    snapshot = sale.receipt_snapshot

    assert snapshot["totals"] == {
        "subtotal": "20.00",
        "discount_total": "5.00",
        "total": "15.00",
        "currency": "MXN",
    }

    assert snapshot["authorizer"] == {
        "staff_id": manager.id,
        "display_name": manager.display_name,
    }


def test_checkout_retry_does_not_replace_receipt_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-retry",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Receipt Retry Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="RECEIPT-RETRY",
        sale_price="11.00",
    )

    payload = _card_payload(
        sale_uuid="receipt-retry-sale",
        payment_uuid="receipt-retry-payment",
        item_id=item.id,
        presentation_id=presentation.id,
    )

    first = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-RETRY",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(first)

    frozen = deepcopy(
        first.receipt_snapshot
    )

    assert frozen is not None

    item.name = "CHANGED"
    presentation.sale_price = Decimal(
        "500.00"
    )
    db_session.commit()

    retry = RetailSaleService.checkout(
        db_session,
        payload=payload,
        staff=cashier,
        terminal_id="PAP-RETRY",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(retry)

    assert retry.id == first.id
    assert (
        retry.receipt_snapshot
        == frozen
    )
