from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.pos_audit import PosAuditEvent
from app.models.pos_cash import PosCashLedgerEntry
from app.models.retail_inventory import (
    RetailInventoryMovement,
)
from app.models.retail_sales import (
    RetailReturn,
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

from test_retail_checkout import (
    _branch,
    _manager_with_real_pin,
    _product,
    _service_item,
    _staff,
)


def _return_payload(
    *,
    return_uuid: str,
    sale_line_id: int,
    quantity: str,
    refund_method: str = "CARD",
    reason: str = "Customer return",
    external_reference: str | None = None,
):
    return SimpleNamespace(
        return_uuid=return_uuid,
        reason=reason,
        refund_method=refund_method,
        external_reference=external_reference,
        lines=[
            SimpleNamespace(
                sale_line_id=sale_line_id,
                quantity=Decimal(quantity),
            )
        ],
    )


def _paid_card_product(
    db_session,
    *,
    suffix: str,
    quantity: str = "3.000",
    sale_price: str = "10.00",
):
    branch = _branch(
        db_session,
        f"return-{suffix}",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name=f"Cashier {suffix}",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name=f"Manager {suffix}",
        pin="2468",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku=f"RET-{suffix}",
        sale_price=sale_price,
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=RetailCheckoutRequest(
            sale_uuid=f"sale-{suffix}",
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
                "0.00"
            ),
            payment_uuid=f"pay-{suffix}",
            payment_method="CARD",
            amount_tendered=None,
            external_reference=(
                f"CARD-{suffix}"
            ),
        ),
        staff=cashier,
        terminal_id=f"PAP-{suffix}",
        manager=None,
    )

    db_session.commit()
    db_session.refresh(sale)
    db_session.refresh(balance)

    return (
        branch,
        cashier,
        manager,
        sale,
        item,
        presentation,
        balance,
    )


def test_return_requires_manager(
    db_session,
):
    (
        _branch_row,
        cashier,
        _manager,
        sale,
        _item,
        _presentation,
        _balance,
    ) = _paid_card_product(
        db_session,
        suffix="manager-required",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.return_items(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_return_payload(
                return_uuid=(
                    "return-manager-required"
                ),
                sale_line_id=(
                    sale.lines[0].id
                ),
                quantity="1.000",
            ),
            staff=cashier,
            manager=None,
        )

    assert exc.value.status_code == 403


def test_partial_product_return_restores_stock_and_audits(
    db_session,
):
    (
        branch,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        balance,
    ) = _paid_card_product(
        db_session,
        suffix="partial",
    )

    after_sale = Decimal(
        balance.quantity_on_hand
    )

    returned = (
        RetailSaleService.return_items(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_return_payload(
                return_uuid="return-partial",
                sale_line_id=(
                    sale.lines[0].id
                ),
                quantity="1.000",
                reason=(
                    "Customer changed mind"
                ),
                external_reference=(
                    "CARD-REFUND-001"
                ),
            ),
            staff=cashier,
            manager=manager,
        )
    )

    db_session.commit()
    db_session.refresh(balance)
    db_session.refresh(sale)

    assert returned.sale_id == sale.id

    assert (
        balance.quantity_on_hand
        == after_sale
        + Decimal("1.000")
    )

    assert sale.status == (
        "PARTIALLY_RETURNED"
    )

    movements = (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id,
            RetailInventoryMovement.movement_type
            == "RETURN",
        )
        .all()
    )

    assert len(movements) == 1
    assert (
        Decimal(
            movements[0].quantity_delta
        )
        == Decimal("1.000")
    )

    events = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type
            == "RETAIL_RETURN_AUTHORIZED"
        )
        .all()
    )

    assert len(events) == 1

    event = events[0]

    assert event.branch_id == branch.id
    assert (
        event.actor_staff_id
        == cashier.id
    )
    assert (
        event.authorizer_staff_id
        == manager.id
    )
    assert (
        event.target_type
        == "retail_sale"
    )
    assert (
        event.target_id
        == sale.sale_uuid
    )

    assert (
        event.metadata_json["reason"]
        == "Customer changed mind"
    )
    assert (
        event.metadata_json[
            "refund_amount"
        ]
        == "10.00"
    )


def test_repeated_partial_return_cannot_exceed_remaining_quantity(
    db_session,
):
    (
        _branch_row,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        balance,
    ) = _paid_card_product(
        db_session,
        suffix="limit",
        quantity="2.000",
    )

    after_sale = Decimal(
        balance.quantity_on_hand
    )

    RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_return_payload(
            return_uuid="return-limit-1",
            sale_line_id=sale.lines[0].id,
            quantity="1.000",
            external_reference="REF-LIMIT-1",
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.return_items(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_return_payload(
                return_uuid="return-limit-2",
                sale_line_id=(
                    sale.lines[0].id
                ),
                quantity="2.000",
                external_reference=(
                    "REF-LIMIT-2"
                ),
            ),
            staff=cashier,
            manager=manager,
        )

    db_session.rollback()

    assert exc.value.status_code == 409

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == after_sale
        + Decimal("1.000")
    )

    assert (
        db_session.query(RetailReturn)
        .filter(
            RetailReturn.sale_id
            == sale.id
        )
        .count()
        == 1
    )


def test_full_return_marks_sale_returned(
    db_session,
):
    (
        _branch_row,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        _balance,
    ) = _paid_card_product(
        db_session,
        suffix="full",
        quantity="2.000",
    )

    RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_return_payload(
            return_uuid="return-full",
            sale_line_id=sale.lines[0].id,
            quantity="2.000",
            external_reference="REF-FULL",
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()
    db_session.refresh(sale)

    assert sale.status == "RETURNED"


def test_service_return_has_no_inventory_effect(
    db_session,
):
    branch = _branch(
        db_session,
        "return-service",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Service Return Cashier",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="Service Return Manager",
        pin="2468",
    )

    item = _service_item(
        db_session,
        branch=branch,
        sku="COPY-RETURN",
    )

    sale = RetailSaleService.checkout(
        db_session,
        payload=RetailCheckoutRequest(
            sale_uuid="service-return-sale",
            held_sale_uuid=None,
            lines=[
                RetailCheckoutLineInput(
                    item_id=item.id,
                    presentation_id=None,
                    quantity=Decimal(
                        "21.000"
                    ),
                    discount_amount=Decimal(
                        "0.00"
                    ),
                )
            ],
            sale_discount_amount=Decimal(
                "0.00"
            ),
            payment_uuid=(
                "service-return-payment"
            ),
            payment_method="CARD",
            amount_tendered=None,
            external_reference=(
                "CARD-SERVICE-RETURN"
            ),
        ),
        staff=cashier,
        terminal_id="PAP-SERVICE-RETURN",
        manager=None,
    )

    db_session.commit()

    before = (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id
        )
        .count()
    )

    RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_return_payload(
            return_uuid=(
                "service-return-001"
            ),
            sale_line_id=sale.lines[0].id,
            quantity="21.000",
            external_reference=(
                "CARD-SERVICE-REFUND"
            ),
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    after = (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id
        )
        .count()
    )

    assert after == before


def test_cash_return_writes_one_negative_cash_ledger_entry(
    db_session,
):
    branch = _branch(
        db_session,
        "return-cash",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Return Cash Cashier",
    )

    manager = _manager_with_real_pin(
        db_session,
        branch=branch,
        name="Return Cash Manager",
        pin="2468",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="RETURN-CASH",
        sale_price="10.00",
    )

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id="PAP-RETURN-CASH",
        opening_counts=None,
        opening_amount=Decimal("0.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
        module_code="PAPELERIA",
    )

    db_session.commit()

    sale = RetailSaleService.checkout(
        db_session,
        payload=RetailCheckoutRequest(
            sale_uuid="return-cash-sale",
            held_sale_uuid=None,
            lines=[
                RetailCheckoutLineInput(
                    item_id=item.id,
                    presentation_id=(
                        presentation.id
                    ),
                    quantity=Decimal(
                        "2.000"
                    ),
                    discount_amount=Decimal(
                        "0.00"
                    ),
                )
            ],
            sale_discount_amount=Decimal(
                "0.00"
            ),
            payment_uuid=(
                "return-cash-sale-payment"
            ),
            payment_method="CASH",
            amount_tendered=Decimal(
                "20.00"
            ),
            external_reference=None,
        ),
        staff=cashier,
        terminal_id="PAP-RETURN-CASH",
        manager=None,
    )

    db_session.commit()

    RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_return_payload(
            return_uuid=(
                "return-cash-refund"
            ),
            sale_line_id=sale.lines[0].id,
            quantity="1.000",
            refund_method="CASH",
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    entries = (
        db_session.query(
            PosCashLedgerEntry
        )
        .filter(
            PosCashLedgerEntry.shift_id
            == shift.id,
            PosCashLedgerEntry.idempotency_key
            == (
                "retail-return:"
                "return-cash-refund"
            ),
        )
        .all()
    )

    assert len(entries) == 1
    assert (
        Decimal(entries[0].amount)
        == Decimal("-10.00")
    )


def test_return_retry_is_idempotent(
    db_session,
):
    (
        _branch_row,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        balance,
    ) = _paid_card_product(
        db_session,
        suffix="retry",
        quantity="2.000",
    )

    after_sale = Decimal(
        balance.quantity_on_hand
    )

    payload = _return_payload(
        return_uuid="return-retry",
        sale_line_id=sale.lines[0].id,
        quantity="1.000",
        external_reference="REF-RETRY",
    )

    first = RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=payload,
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    second = RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=payload,
        staff=cashier,
        manager=manager,
    )

    db_session.commit()
    db_session.refresh(balance)

    assert first.id == second.id

    assert (
        balance.quantity_on_hand
        == after_sale
        + Decimal("1.000")
    )

    assert (
        db_session.query(RetailReturn)
        .filter(
            RetailReturn.sale_id
            == sale.id
        )
        .count()
        == 1
    )

    assert (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id,
            RetailInventoryMovement.movement_type
            == "RETURN",
        )
        .count()
        == 1
    )


def test_return_request_requires_manager_pin_schema():
    from pydantic import ValidationError

    from app.schemas.retail_sales import (
        RetailReturnRequest,
    )

    with pytest.raises(ValidationError):
        RetailReturnRequest(
            return_uuid="schema-return",
            reason="Return",
            refund_method="CARD",
            external_reference="REF",
            authorizing_manager_staff_id=1,
            lines=[
                {
                    "sale_line_id": 1,
                    "quantity": "1.000",
                }
            ],
        )


def test_return_route_is_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    assert (
        "/retail/sales/{sale_uuid}/returns"
        in paths
    )
    assert (
        "post"
        in paths[
            "/retail/sales/"
            "{sale_uuid}/returns"
        ]
    )
