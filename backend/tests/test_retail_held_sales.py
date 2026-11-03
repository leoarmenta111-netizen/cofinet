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
from app.services.retail_sale_service import (
    RetailSaleService,
)
from app.schemas.retail_sales import (
    RetailHeldSaleLineInput,
    RetailHeldSaleUpsert,
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
    module_code: str = "PAPELERIA",
) -> PosStaff:
    staff = PosStaff(
        branch_id=branch.id,
        module_code=module_code,
        display_name=name,
        role="CASHIER",
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
    price: str = "10.00",
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
        category="Test",
        base_unit_code="PIECE",
        cost=Decimal("4.00"),
        inventory_tracked=True,
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("100.000"),
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
        sale_price=Decimal(price),
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
        quantity_on_hand=Decimal("25.000"),
        low_stock_threshold=Decimal("5.000"),
        max_stock=Decimal("100.000"),
    )

    db_session.add(balance)
    db_session.commit()

    db_session.refresh(item)
    db_session.refresh(presentation)
    db_session.refresh(balance)

    return item, presentation, balance


def _payload(
    *,
    item: RetailCatalogItem,
    presentation: RetailPresentation,
    quantity: str,
    label: str | None = None,
) -> RetailHeldSaleUpsert:
    return RetailHeldSaleUpsert(
        label=label,
        lines=[
            RetailHeldSaleLineInput(
                item_id=item.id,
                presentation_id=presentation.id,
                quantity=Decimal(quantity),
            )
        ],
    )


def test_hold_creates_held_sale_with_preview_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "held-create",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier A",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-001",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="2.000",
            label="Cliente mostrador",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()
    db_session.refresh(sale)

    assert sale.id is not None
    assert sale.sale_uuid
    assert sale.branch_id == branch.id
    assert sale.module_code == "PAPELERIA"
    assert sale.terminal_id == "PAP-T1"
    assert sale.cashier_staff_id == staff.id
    assert sale.status == "HELD"
    assert sale.label == "Cliente mostrador"
    assert sale.receipt_snapshot is None

    assert sale.subtotal == Decimal("20.00")
    assert sale.discount_total == Decimal("0.00")
    assert sale.total == Decimal("20.00")

    assert len(sale.lines) == 1

    line = sale.lines[0]

    assert line.item_id == item.id
    assert line.presentation_id == presentation.id
    assert line.quantity == Decimal("2.000")
    assert line.unit_price == Decimal("10.00")
    assert line.line_total == Decimal("20.00")


def test_update_held_sale_replaces_lines_and_label(
    db_session,
):
    branch = _branch(
        db_session,
        "held-update",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier Update",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-002",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
            label="Original",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    updated = RetailSaleService.update_held(
        db_session,
        sale_uuid=sale.sale_uuid,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="3.000",
            label="Actualizada",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()
    db_session.refresh(updated)

    assert updated.id == sale.id
    assert updated.status == "HELD"
    assert updated.label == "Actualizada"
    assert updated.subtotal == Decimal("30.00")
    assert updated.total == Decimal("30.00")

    assert len(updated.lines) == 1
    assert updated.lines[0].quantity == Decimal("3.000")
    assert updated.lines[0].line_total == Decimal("30.00")


def test_list_held_sales_is_scoped_to_staff_branch(
    db_session,
):
    branch_a = _branch(
        db_session,
        "held-list-a",
    )

    branch_b = _branch(
        db_session,
        "held-list-b",
    )

    staff_a = _staff(
        db_session,
        branch=branch_a,
        name="Cashier A",
    )

    staff_b = _staff(
        db_session,
        branch=branch_b,
        name="Cashier B",
    )

    item_a, presentation_a, _ = _product(
        db_session,
        branch=branch_a,
        sku="HELD-LIST-A",
    )

    item_b, presentation_b, _ = _product(
        db_session,
        branch=branch_b,
        sku="HELD-LIST-B",
    )

    sale_a = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item_a,
            presentation=presentation_a,
            quantity="1.000",
            label="A",
        ),
        staff=staff_a,
        terminal_id="PAP-A",
    )

    RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item_b,
            presentation=presentation_b,
            quantity="1.000",
            label="B",
        ),
        staff=staff_b,
        terminal_id="PAP-B",
    )

    db_session.commit()

    rows = RetailSaleService.list_held(
        db_session,
        staff=staff_a,
    )

    assert len(rows) == 1
    assert rows[0].id == sale_a.id
    assert rows[0].branch_id == branch_a.id
    assert rows[0].module_code == "PAPELERIA"


def test_resume_returns_same_held_sale(
    db_session,
):
    branch = _branch(
        db_session,
        "held-resume",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier Resume",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-RESUME",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="2.000",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    resumed = RetailSaleService.resume(
        db_session,
        sale_uuid=sale.sale_uuid,
        staff=staff,
    )

    assert resumed.id == sale.id
    assert resumed.sale_uuid == sale.sale_uuid
    assert resumed.status == "HELD"


def test_other_branch_cannot_resume_held_sale(
    db_session,
):
    branch_a = _branch(
        db_session,
        "held-resume-a",
    )

    branch_b = _branch(
        db_session,
        "held-resume-b",
    )

    staff_a = _staff(
        db_session,
        branch=branch_a,
        name="Cashier Resume A",
    )

    staff_b = _staff(
        db_session,
        branch=branch_b,
        name="Cashier Resume B",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch_a,
        sku="HELD-PRIVATE",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
        ),
        staff=staff_a,
        terminal_id="PAP-A",
    )

    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        RetailSaleService.resume(
            db_session,
            sale_uuid=sale.sale_uuid,
            staff=staff_b,
        )

    assert exc.value.status_code == 404


def test_cafe_staff_cannot_create_papeleria_held_sale(
    db_session,
):
    branch = _branch(
        db_session,
        "held-module",
    )

    cafe_staff = _staff(
        db_session,
        branch=branch,
        name="Cafe Cashier",
        module_code="CAFE",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-MODULE",
    )

    with pytest.raises(HTTPException) as exc:
        RetailSaleService.hold(
            db_session,
            payload=_payload(
                item=item,
                presentation=presentation,
                quantity="1.000",
            ),
            staff=cafe_staff,
            terminal_id="CAFE-T1",
        )

    assert exc.value.status_code == 403


def test_held_sale_has_no_inventory_payment_or_cash_effect(
    db_session,
):
    branch = _branch(
        db_session,
        "held-no-effects",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier No Effects",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="HELD-NO-EFFECT",
    )

    before_stock = Decimal(
        balance.quantity_on_hand
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="5.000",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()
    db_session.refresh(balance)

    assert sale.status == "HELD"

    assert Decimal(
        balance.quantity_on_hand
    ) == before_stock

    assert (
        db_session.query(
            RetailInventoryMovement
        ).count()
        == 0
    )

    assert (
        db_session.query(
            RetailPayment
        ).count()
        == 0
    )

    assert (
        db_session.query(
            PosCashLedgerEntry
        ).count()
        == 0
    )


def test_only_held_sale_can_be_updated(
    db_session,
):
    branch = _branch(
        db_session,
        "held-paid-update",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier Paid",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-PAID",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    sale.status = "PAID"
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        RetailSaleService.update_held(
            db_session,
            sale_uuid=sale.sale_uuid,
            payload=_payload(
                item=item,
                presentation=presentation,
                quantity="2.000",
            ),
            staff=staff,
            terminal_id="PAP-T1",
        )

    assert exc.value.status_code == 409


def test_list_held_does_not_return_paid_sales(
    db_session,
):
    branch = _branch(
        db_session,
        "held-list-status",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier List Status",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-LIST-STATUS",
    )

    held = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
            label="Keep",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    paid = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
            label="Hide",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    paid.status = "PAID"
    db_session.commit()

    rows = RetailSaleService.list_held(
        db_session,
        staff=staff,
    )

    assert [row.id for row in rows] == [
        held.id
    ]


def test_held_sale_row_exists_without_payment(
    db_session,
):
    branch = _branch(
        db_session,
        "held-persisted",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cashier Persisted",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HELD-PERSIST",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    persisted = db_session.query(
        RetailSale
    ).filter(
        RetailSale.sale_uuid
        == sale.sale_uuid
    ).one()

    assert persisted.status == "HELD"
    assert persisted.payments == []


from app.auth.pos_staff_security import (
    get_current_pos_staff,
)
from app.auth.security import get_current_token
from app.main import app


def _api_request(
    *,
    client,
    staff,
    branch,
    terminal_id="PAP-T1",
    method,
    path,
    json=None,
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
        return client.request(
            method,
            path,
            json=json,
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


def test_http_create_held_sale(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-create",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP Create Cashier",
    )

    item, presentation, balance = _product(
        db_session,
        branch=branch,
        sku="HTTP-HELD-001",
    )

    before_stock = Decimal(
        balance.quantity_on_hand
    )

    response = _api_request(
        client=client,
        staff=staff,
        branch=branch,
        method="POST",
        path="/retail/sales/held",
        json={
            "label": "Mostrador 1",
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": (
                        presentation.id
                    ),
                    "quantity": "2.000",
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "HELD"
    assert body["module_code"] == "PAPELERIA"
    assert body["terminal_id"] == "PAP-T1"
    assert body["label"] == "Mostrador 1"
    assert body["total"] == "20.00"
    assert len(body["lines"]) == 1

    db_session.refresh(balance)

    assert Decimal(
        balance.quantity_on_hand
    ) == before_stock

    assert (
        db_session.query(
            RetailPayment
        ).count()
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


def test_http_update_held_sale(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-update",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP Update Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-HELD-002",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
            label="Antes",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    response = _api_request(
        client=client,
        staff=staff,
        branch=branch,
        terminal_id="PAP-T2",
        method="PUT",
        path=(
            "/retail/sales/held/"
            f"{sale.sale_uuid}"
        ),
        json={
            "label": "Después",
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": (
                        presentation.id
                    ),
                    "quantity": "3.000",
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["sale_uuid"] == sale.sale_uuid
    assert body["status"] == "HELD"
    assert body["terminal_id"] == "PAP-T2"
    assert body["label"] == "Después"
    assert body["total"] == "30.00"
    assert body["lines"][0]["quantity"] == "3.000"


def test_http_list_held_sales(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-list",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP List Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-LIST-001",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
            label="Pendiente",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    response = _api_request(
        client=client,
        staff=staff,
        branch=branch,
        method="GET",
        path="/retail/sales/held",
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["sale_uuid"] == sale.sale_uuid
    assert body[0]["status"] == "HELD"


def test_http_get_held_sale_by_uuid(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-get",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP Get Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-GET-001",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="2.000",
            label="Recuperar",
        ),
        staff=staff,
        terminal_id="PAP-T1",
    )

    db_session.commit()

    response = _api_request(
        client=client,
        staff=staff,
        branch=branch,
        method="GET",
        path=(
            "/retail/sales/"
            f"{sale.sale_uuid}"
        ),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["sale_uuid"] == sale.sale_uuid
    assert body["label"] == "Recuperar"
    assert body["status"] == "HELD"


def test_http_other_branch_cannot_get_sale(
    client,
    db_session,
):
    branch_a = _branch(
        db_session,
        "held-http-private-a",
    )

    branch_b = _branch(
        db_session,
        "held-http-private-b",
    )

    staff_a = _staff(
        db_session,
        branch=branch_a,
        name="HTTP Private A",
    )

    staff_b = _staff(
        db_session,
        branch=branch_b,
        name="HTTP Private B",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch_a,
        sku="HTTP-PRIVATE-001",
    )

    sale = RetailSaleService.hold(
        db_session,
        payload=_payload(
            item=item,
            presentation=presentation,
            quantity="1.000",
        ),
        staff=staff_a,
        terminal_id="PAP-A",
    )

    db_session.commit()

    response = _api_request(
        client=client,
        staff=staff_b,
        branch=branch_b,
        method="GET",
        path=(
            "/retail/sales/"
            f"{sale.sale_uuid}"
        ),
    )

    assert response.status_code == 404


def test_http_cafe_staff_cannot_create_held_sale(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-cafe",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP Cafe Cashier",
        module_code="CAFE",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-CAFE-001",
    )

    response = _api_request(
        client=client,
        staff=staff,
        branch=branch,
        terminal_id="CAFE-T1",
        method="POST",
        path="/retail/sales/held",
        json={
            "lines": [
                {
                    "item_id": item.id,
                    "presentation_id": (
                        presentation.id
                    ),
                    "quantity": "1.000",
                }
            ],
        },
    )

    assert response.status_code == 403


def test_http_held_sale_requires_terminal_context(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "held-http-terminal",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="HTTP Terminal Cashier",
    )

    item, presentation, _ = _product(
        db_session,
        branch=branch,
        sku="HTTP-TERM-001",
    )

    def current_staff_override():
        return staff

    def bad_token_override():
        return {
            "branch_code": branch.code,
        }

    app.dependency_overrides[
        get_current_pos_staff
    ] = current_staff_override

    app.dependency_overrides[
        get_current_token
    ] = bad_token_override

    try:
        response = client.post(
            "/retail/sales/held",
            json={
                "lines": [
                    {
                        "item_id": item.id,
                        "presentation_id": (
                            presentation.id
                        ),
                        "quantity": "1.000",
                    }
                ],
            },
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

    assert response.status_code == 401
