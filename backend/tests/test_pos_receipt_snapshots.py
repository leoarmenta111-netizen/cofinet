from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.pos_orders import PosOrderCreate
from app.schemas.pos_receipts import ReceiptSnapshotV1


def legacy_payload():
    now = datetime.now(timezone.utc)

    return {
        "order_uuid": str(uuid4()),
        "branch_code": "nuevo-vallarta",
        "terminal_id": "POS-TEST-01",
        "created_at_client": now.isoformat(),
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "modifier_option_ids": [],
            }
        ],
        "payment": {
            "payment_uuid": str(uuid4()),
            "method": "CASH",
            "amount_tendered": "100.00",
            "created_at_client": now.isoformat(),
        },
    }


def frozen_snapshot(
    *,
    order_uuid,
    folio,
):
    now = datetime.now(timezone.utc)

    return {
        "schema_version": 1,
        "order_uuid": str(order_uuid),
        "folio": folio,
        "sold_at": now.isoformat(),
        "currency": "MXN",
        "business": {
            "business_name": "CofiCenter",
            "logo_ref": None,
            "phone": None,
            "web_social": None,
            "footer_message": "Gracias por su compra",
        },
        "branch": {
            "branch_code": "nuevo-vallarta",
            "branch_name": "Nuevo Vallarta",
            "address": None,
            "phone": None,
        },
        "terminal": {
            "terminal_id": "POS-TEST-01",
        },
        "customer": None,
        "items": [
            {
                "product_id": 1,
                "product_name": "Americano",
                "quantity": 1,
                "unit_price_cents": 10000,
                "line_total_cents": 10000,
                "modifiers": [],
            }
        ],
        "totals": {
            "subtotal_cents": 10000,
            "discount_cents": 0,
            "tax_mode": "NONE",
            "tax_rate": "0.0000",
            "tax_cents": 0,
            "tip_cents": 0,
            "total_cents": 10000,
        },
        "payment": {
            "method": "CASH",
            "amount_cents": 10000,
            "amount_tendered_cents": 10000,
            "change_due_cents": 0,
        },
    }


def test_legacy_payload_without_receipt_fields_is_still_valid():
    payload = PosOrderCreate.model_validate(
        legacy_payload()
    )

    assert payload.folio is None
    assert payload.receipt_snapshot is None


def test_frozen_payload_requires_and_preserves_folio_and_snapshot():
    order_uuid = uuid4()
    folio = "NV-260908-7K3M9Q2F"

    data = legacy_payload()
    data["order_uuid"] = str(order_uuid)
    data["folio"] = folio
    data["receipt_snapshot"] = frozen_snapshot(
        order_uuid=order_uuid,
        folio=folio,
    )

    payload = PosOrderCreate.model_validate(data)

    assert payload.folio == folio
    assert isinstance(
        payload.receipt_snapshot,
        ReceiptSnapshotV1,
    )
    assert (
        str(payload.receipt_snapshot.order_uuid)
        == str(order_uuid)
    )
    assert payload.receipt_snapshot.folio == folio


@pytest.mark.parametrize(
    "present_field",
    [
        "folio",
        "receipt_snapshot",
    ],
)
def test_frozen_payload_rejects_only_one_receipt_field(
    present_field,
):
    order_uuid = uuid4()
    folio = "NV-260908-7K3M9Q2F"

    data = legacy_payload()
    data["order_uuid"] = str(order_uuid)

    if present_field == "folio":
        data["folio"] = folio
    else:
        data["receipt_snapshot"] = frozen_snapshot(
            order_uuid=order_uuid,
            folio=folio,
        )

    with pytest.raises(ValidationError):
        PosOrderCreate.model_validate(data)


from decimal import Decimal

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.services.pos_order_service import PosOrderService


def seed_frozen_catalog(db):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Receipt Branch {suffix}",
        code=f"receipt-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Receipt Category {suffix}",
        slug=f"receipt-category-{suffix}",
        is_active=True,
    )

    db.add_all([branch, category])
    db.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Frozen Americano {suffix}",
        base_price=Decimal("100.00"),
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

    db.flush()

    return branch, product


def frozen_order_payload(
    branch,
    product,
    *,
    order_uuid=None,
    folio="NV-260908-7K3M9Q2F",
):
    now = datetime.now(timezone.utc)
    order_uuid = order_uuid or uuid4()

    snapshot = {
        "schema_version": 1,
        "order_uuid": str(order_uuid),
        "folio": folio,
        "sold_at": now.isoformat(),
        "currency": "MXN",
        "business": {
            "business_name": "CofiCenter",
            "logo_ref": None,
            "phone": None,
            "web_social": None,
            "footer_message": "Gracias",
        },
        "branch": {
            "branch_code": branch.code,
            "branch_name": branch.name,
            "address": None,
            "phone": None,
        },
        "terminal": {
            "terminal_id": "POS-FROZEN-01",
        },
        "customer": None,
        "items": [
            {
                "product_id": product.id,
                "product_name": product.name,
                "quantity": 1,
                "unit_price_cents": 10000,
                "line_total_cents": 10000,
                "modifiers": [],
            }
        ],
        "totals": {
            "subtotal_cents": 10000,
            "discount_cents": 0,
            "tax_mode": "NONE",
            "tax_rate": "0.0000",
            "tax_cents": 0,
            "tip_cents": 0,
            "total_cents": 10000,
        },
        "payment": {
            "method": "CASH",
            "amount_cents": 10000,
            "amount_tendered_cents": 10000,
            "change_due_cents": 0,
        },
    }

    return PosOrderCreate.model_validate(
        {
            "order_uuid": str(order_uuid),
            "branch_code": branch.code,
            "terminal_id": "POS-FROZEN-01",
            "created_at_client": now.isoformat(),
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "modifier_option_ids": [],
                }
            ],
            "payment": {
                "payment_uuid": str(uuid4()),
                "method": "CASH",
                "amount_tendered": "100.00",
                "created_at_client": now.isoformat(),
            },
            "folio": folio,
            "receipt_snapshot": snapshot,
        }
    )


def test_frozen_sale_preserves_client_generated_folio(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    folio = "NV-260908-ABC12345"

    result = PosOrderService.create(
        db_session,
        frozen_order_payload(
            branch,
            product,
            folio=folio,
        ),
    )

    assert result.folio == folio


def test_frozen_sale_persists_one_immutable_receipt_snapshot(
    db_session,
):
    from app.models.pos_orders import PosOrder
    from app.models.pos_receipts import PosReceiptSnapshot

    branch, product = seed_frozen_catalog(
        db_session
    )

    order_uuid = uuid4()
    folio = "NV-260908-SNAP0001"

    payload = frozen_order_payload(
        branch,
        product,
        order_uuid=order_uuid,
        folio=folio,
    )

    result = PosOrderService.create(
        db_session,
        payload,
    )

    stored_order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid == str(order_uuid)
        )
        .one()
    )

    rows = (
        db_session.query(PosReceiptSnapshot)
        .filter(
            PosReceiptSnapshot.order_id
            == stored_order.id
        )
        .all()
    )

    assert result.folio == folio
    assert len(rows) == 1

    receipt = rows[0]

    assert receipt.schema_version == 1
    assert receipt.snapshot_json["schema_version"] == 1
    assert receipt.snapshot_json["order_uuid"] == str(order_uuid)
    assert receipt.snapshot_json["folio"] == folio

    retry = PosOrderService.create(
        db_session,
        payload,
    )

    assert retry.order_uuid == str(order_uuid)
    assert retry.folio == folio

    assert (
        db_session.query(PosReceiptSnapshot)
        .filter(
            PosReceiptSnapshot.order_id
            == stored_order.id
        )
        .count()
        == 1
    )


def test_frozen_sale_does_not_reprice_from_current_catalog(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    # El POS ya cobró esta venta en 100.00.
    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-FROZEN01",
    )

    # Antes de sincronizar, el catálogo cambia a 150.00.
    product.base_price = Decimal("150.00")
    db_session.flush()

    result = PosOrderService.create(
        db_session,
        payload,
    )

    assert result.subtotal == Decimal("100.00")
    assert result.total == Decimal("100.00")
    assert len(result.items) == 1
    assert result.items[0].unit_price == Decimal("100.00")
    assert result.items[0].line_total == Decimal("100.00")
    assert result.payment.amount == Decimal("100.00")


from app.models.pos_catalog import (
    PosModifierGroup,
    PosModifierOption,
    PosProductModifierGroup,
)
from app.models.pos_orders import PosOrder
from app.models.pos_receipts import PosReceiptSnapshot


def test_frozen_modifier_price_delta_is_not_repriced(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    suffix = uuid4().hex[:8]

    group = PosModifierGroup(
        name=f"Milk {suffix}",
        required=False,
        min_select=0,
        max_select=1,
        is_active=True,
    )

    db_session.add(group)
    db_session.flush()

    option = PosModifierOption(
        group_id=group.id,
        name=f"Oat Milk {suffix}",
        price_delta=Decimal("10.00"),
        is_active=True,
    )

    link = PosProductModifierGroup(
        product_id=product.id,
        modifier_group_id=group.id,
        sort_order=0,
    )

    db_session.add_all([
        option,
        link,
    ])
    db_session.flush()

    order_uuid = uuid4()

    original = frozen_order_payload(
        branch,
        product,
        order_uuid=order_uuid,
        folio="NV-260908-MODFRZ01",
    )

    data = original.model_dump(
        mode="json"
    )

    data["items"][0][
        "modifier_option_ids"
    ] = [option.id]

    snapshot_item = (
        data["receipt_snapshot"]["items"][0]
    )

    snapshot_item["modifiers"] = [
        {
            "modifier_group_id": group.id,
            "modifier_option_id": option.id,
            "group_name": group.name,
            "option_name": option.name,
            "price_delta_cents": 1000,
        }
    ]

    snapshot_item[
        "unit_price_cents"
    ] = 11000

    snapshot_item[
        "line_total_cents"
    ] = 11000

    totals = data[
        "receipt_snapshot"
    ]["totals"]

    totals["subtotal_cents"] = 11000
    totals["total_cents"] = 11000

    snapshot_payment = data[
        "receipt_snapshot"
    ]["payment"]

    snapshot_payment[
        "amount_cents"
    ] = 11000

    snapshot_payment[
        "amount_tendered_cents"
    ] = 11000

    snapshot_payment[
        "change_due_cents"
    ] = 0

    data["payment"][
        "amount_tendered"
    ] = "110.00"

    payload = PosOrderCreate.model_validate(
        data
    )

    # Catalog changes after the customer
    # already paid the frozen sale.
    option.price_delta = Decimal("25.00")
    db_session.flush()

    result = PosOrderService.create(
        db_session,
        payload,
    )

    assert result.subtotal == Decimal("110.00")
    assert result.total == Decimal("110.00")

    assert result.items[0].unit_price == Decimal(
        "110.00"
    )

    assert (
        result.items[0]
        .modifiers[0]
        .price_delta
        == Decimal("10.00")
    )

    stored_order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(order_uuid)
        )
        .one()
    )

    receipt = (
        db_session.query(
            PosReceiptSnapshot
        )
        .filter(
            PosReceiptSnapshot.order_id
            == stored_order.id
        )
        .one()
    )

    assert (
        receipt.snapshot_json[
            "items"
        ][0]["modifiers"][0][
            "price_delta_cents"
        ]
        == 1000
    )


def test_frozen_sale_rejects_inconsistent_line_total(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADLINE1",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "items"
    ][0]["line_total_cents"] = 9999

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_inconsistent_subtotal(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADSUB01",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "totals"
    ]["subtotal_cents"] = 9999

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    (
        "tax_mode",
        "tax_rate",
        "bad_tax_cents",
        "bad_total_cents",
        "bad_tendered",
    ),
    [
        (
            "NONE",
            "0",
            1,
            10001,
            "100.01",
        ),
        (
            "ADDED",
            "0.16",
            1500,
            11500,
            "115.00",
        ),
        (
            "INCLUDED",
            "0.16",
            1300,
            10000,
            "100.00",
        ),
    ],
)
def test_frozen_sale_rejects_inconsistent_tax(
    db_session,
    tax_mode,
    tax_rate,
    bad_tax_cents,
    bad_total_cents,
    bad_tendered,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio=(
            "NV-260908-BADTAX"
            f"{tax_mode[:3]}"
        ),
    )

    data = payload.model_dump(
        mode="json"
    )

    totals = data[
        "receipt_snapshot"
    ]["totals"]

    totals["tax_mode"] = tax_mode
    totals["tax_rate"] = tax_rate
    totals["tax_cents"] = bad_tax_cents
    totals["total_cents"] = bad_total_cents

    snapshot_payment = data[
        "receipt_snapshot"
    ]["payment"]

    snapshot_payment[
        "amount_cents"
    ] = bad_total_cents

    snapshot_payment[
        "amount_tendered_cents"
    ] = bad_total_cents

    snapshot_payment[
        "change_due_cents"
    ] = 0

    data["payment"][
        "amount_tendered"
    ] = bad_tendered

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_inconsistent_final_total(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADTOTAL1",
    )

    data = payload.model_dump(
        mode="json"
    )

    totals = data[
        "receipt_snapshot"
    ]["totals"]

    totals["subtotal_cents"] = 10000
    totals["discount_cents"] = 1000
    totals["tax_mode"] = "ADDED"
    totals["tax_rate"] = "0.16"
    totals["tax_cents"] = 1440
    totals["tip_cents"] = 500

    # Correct total would be 10940.
    totals["total_cents"] = 10941

    snapshot_payment = data[
        "receipt_snapshot"
    ]["payment"]

    snapshot_payment[
        "amount_cents"
    ] = 10941

    snapshot_payment[
        "amount_tendered_cents"
    ] = 10941

    snapshot_payment[
        "change_due_cents"
    ] = 0

    data["payment"][
        "amount_tendered"
    ] = "109.41"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_payment_amount_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADPAY01",
    )

    data = payload.model_dump(
        mode="json"
    )

    # Sale total is 100.00, but receipt payment
    # incorrectly claims only 99.99 was paid.
    data["receipt_snapshot"][
        "payment"
    ]["amount_cents"] = 9999

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_cash_rejects_inconsistent_change(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADCHG01",
    )

    data = payload.model_dump(
        mode="json"
    )

    snapshot_payment = data[
        "receipt_snapshot"
    ]["payment"]

    snapshot_payment[
        "amount_cents"
    ] = 10000

    snapshot_payment[
        "amount_tendered_cents"
    ] = 12000

    # Correct change would be 2000.
    snapshot_payment[
        "change_due_cents"
    ] = 1500

    data["payment"][
        "amount_tendered"
    ] = "120.00"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_snapshot_branch_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADBRN01",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "branch"
    ]["branch_code"] = "OTHER-BRANCH"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_snapshot_terminal_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADTERM1",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "terminal"
    ]["terminal_id"] = "OTHER-TERMINAL"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_snapshot_payment_method_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADPMT01",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "payment"
    ]["method"] = "CARD_EXTERNAL"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_snapshot_order_uuid_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-BADUUID1",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "order_uuid"
    ] = str(uuid4())

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_snapshot_folio_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260908-GOODFOL1",
    )

    data = payload.model_dump(
        mode="json"
    )

    data["receipt_snapshot"][
        "folio"
    ] = "NV-260908-WRONGF01"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400


def test_frozen_sale_rejects_duplicate_folio_with_409(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    folio = "NV-260908-DUPFOL01"

    first = frozen_order_payload(
        branch,
        product,
        order_uuid=uuid4(),
        folio=folio,
    )

    PosOrderService.create(
        db_session,
        first,
    )

    second = frozen_order_payload(
        branch,
        product,
        order_uuid=uuid4(),
        folio=folio,
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            second,
        )

    assert exc.value.status_code == 409
    assert "folio" in exc.value.detail.lower()


def test_get_receipt_returns_stored_snapshot_exactly(
    db_session,
    client,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    order_uuid = uuid4()

    payload = frozen_order_payload(
        branch,
        product,
        order_uuid=order_uuid,
        folio="NV-260909-GETRCPT1",
    )

    PosOrderService.create(
        db_session,
        payload,
    )

    response = client.get(
        f"/pos/receipts/{order_uuid}",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 200

    assert response.json() == (
        payload.receipt_snapshot.model_dump(
            mode="json"
        )
    )


def test_get_receipt_rejects_wrong_branch(
    db_session,
    client,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    order_uuid = uuid4()

    payload = frozen_order_payload(
        branch,
        product,
        order_uuid=order_uuid,
        folio="NV-260909-WRNGBR01",
    )

    PosOrderService.create(
        db_session,
        payload,
    )

    response = client.get(
        f"/pos/receipts/{order_uuid}",
        params={
            "branch_code": "other-branch",
        },
    )

    assert response.status_code == 404


def test_get_receipt_unknown_uuid_returns_404(
    db_session,
    client,
):
    branch, _ = seed_frozen_catalog(
        db_session
    )

    missing_uuid = uuid4()

    response = client.get(
        f"/pos/receipts/{missing_uuid}",
        params={
            "branch_code": branch.code,
        },
    )

    assert response.status_code == 404


def test_receipt_customer_snapshot_allows_name_only():
    branch_code = "nuevo-vallarta"

    data = {
        "schema_version": 1,
        "order_uuid": str(uuid4()),
        "folio": "NV-260909-CUSTOM01",
        "sold_at": "2026-09-09T12:00:00-06:00",
        "currency": "MXN",
        "business": {
            "business_name": "CofiCenter",
        },
        "branch": {
            "branch_code": branch_code,
            "branch_name": "Nuevo Vallarta",
        },
        "terminal": {
            "terminal_id": "POS-01",
        },
        "customer": {
            "name": "Customer Name",
            "phone": "5551234567",
        },
        "items": [
            {
                "product_id": 1,
                "product_name": "Coffee",
                "quantity": 1,
                "unit_price_cents": 10000,
                "line_total_cents": 10000,
                "modifiers": [],
            }
        ],
        "totals": {
            "subtotal_cents": 10000,
            "discount_cents": 0,
            "tax_mode": "NONE",
            "tax_rate": "0",
            "tax_cents": 0,
            "tip_cents": 0,
            "total_cents": 10000,
        },
        "payment": {
            "method": "CASH",
            "amount_cents": 10000,
            "amount_tendered_cents": 10000,
            "change_due_cents": 0,
        },
    }

    from pydantic import ValidationError
    from app.schemas.pos_receipts import ReceiptSnapshotV1

    with pytest.raises(ValidationError):
        ReceiptSnapshotV1.model_validate(data)


def test_receipt_snapshot_rejects_unsupported_schema_version():
    branch_code = "nuevo-vallarta"

    data = {
        "schema_version": 2,
        "order_uuid": str(uuid4()),
        "folio": "NV-260909-SCHEMA02",
        "sold_at": "2026-09-09T12:00:00-06:00",
        "currency": "MXN",
        "business": {
            "business_name": "CofiCenter",
        },
        "branch": {
            "branch_code": branch_code,
            "branch_name": "Nuevo Vallarta",
        },
        "terminal": {
            "terminal_id": "POS-01",
        },
        "customer": None,
        "items": [
            {
                "product_id": 1,
                "product_name": "Coffee",
                "quantity": 1,
                "unit_price_cents": 10000,
                "line_total_cents": 10000,
                "modifiers": [],
            }
        ],
        "totals": {
            "subtotal_cents": 10000,
            "discount_cents": 0,
            "tax_mode": "NONE",
            "tax_rate": "0",
            "tax_cents": 0,
            "tip_cents": 0,
            "total_cents": 10000,
        },
        "payment": {
            "method": "CASH",
            "amount_cents": 10000,
            "amount_tendered_cents": 10000,
            "change_due_cents": 0,
        },
    }

    from pydantic import ValidationError
    from app.schemas.pos_receipts import ReceiptSnapshotV1

    with pytest.raises(ValidationError):
        ReceiptSnapshotV1.model_validate(data)


@pytest.mark.parametrize(
    "method",
    [
        "put",
        "patch",
        "delete",
    ],
)
def test_receipt_snapshot_has_no_update_api(
    client,
    method,
):
    request = getattr(client, method)

    response = request(
        f"/pos/receipts/{uuid4()}",
        params={
            "branch_code": "nuevo-vallarta",
        },
    )

    assert response.status_code == 405


def test_frozen_cash_rejects_payload_tender_mismatch(
    db_session,
):
    branch, product = seed_frozen_catalog(
        db_session
    )

    payload = frozen_order_payload(
        branch,
        product,
        folio="NV-260909-TENDER01",
    )

    data = payload.model_dump(
        mode="json"
    )

    # Frozen receipt says customer tendered 100.00
    # with zero change.
    assert (
        data["receipt_snapshot"]["payment"][
            "amount_tendered_cents"
        ]
        == 10000
    )
    assert (
        data["receipt_snapshot"]["payment"][
            "change_due_cents"
        ]
        == 0
    )

    # But queued order payload claims 120.00 was tendered.
    # A frozen sale must reject this disagreement.
    data["payment"]["amount_tendered"] = "120.00"

    invalid = PosOrderCreate.model_validate(
        data
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        PosOrderService.create(
            db_session,
            invalid,
        )

    assert exc.value.status_code == 400
