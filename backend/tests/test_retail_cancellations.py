from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.pos_audit import PosAuditEvent
from app.models.retail_inventory import (
    RetailInventoryMovement,
)
from app.models.retail_sales import (
    RetailSale,
)
from app.services.retail_sale_service import (
    RetailSaleService,
)

from test_retail_returns import (
    _paid_card_product,
    _return_payload,
)


def _cancel_payload(
    *,
    cancellation_uuid: str,
    reason: str = "Manager cancellation",
    refund_method: str = "CARD",
    external_reference: str | None = None,
):
    return SimpleNamespace(
        cancellation_uuid=(
            cancellation_uuid
        ),
        reason=reason,
        refund_method=refund_method,
        external_reference=external_reference,
    )


def test_cancellation_requires_manager(
    db_session,
):
    (
        _branch,
        cashier,
        _manager,
        sale,
        _item,
        _presentation,
        _balance,
    ) = _paid_card_product(
        db_session,
        suffix="cancel-manager",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.cancel_paid_sale(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_cancel_payload(
                cancellation_uuid=(
                    "cancel-manager-required"
                ),
                external_reference=(
                    "CARD-CANCEL-001"
                ),
            ),
            staff=cashier,
            manager=None,
        )

    assert exc.value.status_code == 403


def test_cancellation_keeps_original_sale_and_reverses_remaining_stock(
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
        suffix="cancel-partial-return",
        quantity="3.000",
    )

    original_balance = (
        Decimal(balance.quantity_on_hand)
        + Decimal("3.000")
    )

    RetailSaleService.return_items(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_return_payload(
            return_uuid=(
                "before-cancel-return"
            ),
            sale_line_id=sale.lines[0].id,
            quantity="1.000",
            external_reference=(
                "CARD-BEFORE-CANCEL"
            ),
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    RetailSaleService.cancel_paid_sale(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_cancel_payload(
            cancellation_uuid=(
                "cancel-after-return"
            ),
            reason="Duplicate sale",
            external_reference=(
                "CARD-CANCEL-REMAINING"
            ),
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()
    db_session.refresh(balance)
    db_session.refresh(sale)

    assert sale.status == "CANCELLED"

    assert (
        db_session.query(RetailSale)
        .filter(
            RetailSale.id == sale.id,
            RetailSale.sale_uuid
            == sale.sale_uuid,
        )
        .count()
        == 1
    )

    assert (
        Decimal(balance.quantity_on_hand)
        == original_balance
    )

    reversal = (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id,
            RetailInventoryMovement.movement_type
            == "CANCELLATION_REVERSAL",
        )
        .all()
    )

    assert len(reversal) == 1

    assert (
        Decimal(
            reversal[0].quantity_delta
        )
        == Decimal("2.000")
    )

    events = (
        db_session.query(PosAuditEvent)
        .filter(
            PosAuditEvent.event_type
            == (
                "RETAIL_CANCELLATION_AUTHORIZED"
            )
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
        event.target_id
        == sale.sale_uuid
    )
    assert (
        event.metadata_json["reason"]
        == "Duplicate sale"
    )
    assert (
        event.metadata_json[
            "refund_amount"
        ]
        == "20.00"
    )


def test_cancelled_sale_cannot_be_cancelled_again_with_different_uuid(
    db_session,
):
    (
        _branch,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        _balance,
    ) = _paid_card_product(
        db_session,
        suffix="cancel-twice",
    )

    RetailSaleService.cancel_paid_sale(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_cancel_payload(
            cancellation_uuid=(
                "cancel-twice-1"
            ),
            external_reference=(
                "CARD-CANCEL-1"
            ),
        ),
        staff=cashier,
        manager=manager,
    )

    db_session.commit()

    with pytest.raises(
        HTTPException
    ) as exc:
        RetailSaleService.cancel_paid_sale(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_cancel_payload(
                cancellation_uuid=(
                    "cancel-twice-2"
                ),
                external_reference=(
                    "CARD-CANCEL-2"
                ),
            ),
            staff=cashier,
            manager=manager,
        )

    db_session.rollback()

    assert exc.value.status_code == 409


def test_cancellation_retry_is_idempotent(
    db_session,
):
    (
        _branch,
        cashier,
        manager,
        sale,
        _item,
        _presentation,
        balance,
    ) = _paid_card_product(
        db_session,
        suffix="cancel-retry",
        quantity="2.000",
    )

    original_balance = (
        Decimal(balance.quantity_on_hand)
        + Decimal("2.000")
    )

    payload = _cancel_payload(
        cancellation_uuid=(
            "cancel-retry-id"
        ),
        external_reference=(
            "CARD-CANCEL-RETRY"
        ),
    )

    first = (
        RetailSaleService.cancel_paid_sale(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=payload,
            staff=cashier,
            manager=manager,
        )
    )

    db_session.commit()

    second = (
        RetailSaleService.cancel_paid_sale(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=payload,
            staff=cashier,
            manager=manager,
        )
    )

    db_session.commit()
    db_session.refresh(balance)

    assert first.id == second.id

    assert (
        Decimal(balance.quantity_on_hand)
        == original_balance
    )

    assert (
        db_session.query(
            RetailInventoryMovement
        )
        .filter(
            RetailInventoryMovement.sale_id
            == sale.id,
            RetailInventoryMovement.movement_type
            == "CANCELLATION_REVERSAL",
        )
        .count()
        == 1
    )


def test_cancellation_request_requires_manager_pin_schema():
    from pydantic import ValidationError

    from app.schemas.retail_sales import (
        RetailCancellationRequest,
    )

    with pytest.raises(ValidationError):
        RetailCancellationRequest(
            cancellation_uuid=(
                "schema-cancel"
            ),
            reason="Duplicate",
            refund_method="CARD",
            external_reference="REF",
            authorizing_manager_staff_id=1,
        )


def test_cancellation_route_is_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    assert (
        "/retail/sales/{sale_uuid}/cancel"
        in paths
    )
    assert (
        "post"
        in paths[
            "/retail/sales/"
            "{sale_uuid}/cancel"
        ]
    )
