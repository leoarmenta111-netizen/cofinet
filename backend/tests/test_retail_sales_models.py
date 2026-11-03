from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.branch import Branch
from app.models.pos_staff import PosStaff
from app.models.retail_sales import (
    RetailPayment,
    RetailReturn,
    RetailReturnLine,
    RetailSale,
    RetailSaleLine,
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
) -> PosStaff:
    staff = PosStaff(
        branch_id=branch.id,
        module_code="PAPELERIA",
        display_name=name,
        role="CASHIER",
        pin_hash=f"hash-{name}",
        is_active=True,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _sale(
    db_session,
    *,
    branch: Branch,
    staff: PosStaff,
    sale_uuid: str,
    status: str = "HELD",
) -> RetailSale:
    sale = RetailSale(
        sale_uuid=sale_uuid,
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T1",
        cashier_staff_id=staff.id,
        status=status,
        label=None,
        subtotal=Decimal("100.00"),
        discount_total=Decimal("10.00"),
        total=Decimal("90.00"),
        currency="MXN",
        receipt_snapshot=None,
    )
    db_session.add(sale)
    db_session.commit()
    db_session.refresh(sale)
    return sale


@pytest.mark.parametrize(
    "status",
    [
        "HELD",
        "PAID",
        "PARTIALLY_RETURNED",
        "RETURNED",
        "CANCELLED",
    ],
)
def test_sale_accepts_defined_statuses(
    db_session,
    status,
):
    branch = _branch(
        db_session,
        f"sale-state-{status.lower()}",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name=f"Cashier {status}",
    )

    sale = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid=f"sale-{status}",
        status=status,
    )

    assert sale.id is not None
    assert sale.status == status
    assert sale.module_code == "PAPELERIA"
    assert sale.currency == "MXN"


def test_sale_rejects_unknown_status(
    db_session,
):
    branch = _branch(
        db_session,
        "sale-invalid-state",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Invalid State Cashier",
    )

    sale = RetailSale(
        sale_uuid="sale-invalid",
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T1",
        cashier_staff_id=staff.id,
        status="DELETED",
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
        currency="MXN",
    )

    db_session.add(sale)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_sale_uuid_is_unique(
    db_session,
):
    branch = _branch(
        db_session,
        "sale-uuid-unique",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="UUID Cashier",
    )

    _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="same-sale-uuid",
    )

    duplicate = RetailSale(
        sale_uuid="same-sale-uuid",
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T2",
        cashier_staff_id=staff.id,
        status="HELD",
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
        currency="MXN",
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    (
        "subtotal",
        "discount_total",
        "total",
    ),
    [
        (
            Decimal("-1.00"),
            Decimal("0.00"),
            Decimal("0.00"),
        ),
        (
            Decimal("10.00"),
            Decimal("-1.00"),
            Decimal("10.00"),
        ),
        (
            Decimal("10.00"),
            Decimal("0.00"),
            Decimal("-1.00"),
        ),
    ],
)
def test_sale_rejects_negative_money_totals(
    db_session,
    subtotal,
    discount_total,
    total,
):
    branch = _branch(
        db_session,
        (
            "sale-negative-"
            + str(abs(subtotal + discount_total + total))
            .replace(".", "-")
        ),
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Negative Cashier",
    )

    sale = RetailSale(
        sale_uuid=(
            "negative-"
            + str(subtotal)
            + str(discount_total)
            + str(total)
        ),
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T1",
        cashier_staff_id=staff.id,
        status="HELD",
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        currency="MXN",
    )

    db_session.add(sale)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_sale_line_persists_product_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "sale-line-snapshot",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Line Cashier",
    )
    sale = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="sale-line-1",
    )

    line = RetailSaleLine(
        sale_id=sale.id,
        item_id=None,
        item_type="PRODUCT",
        sku="PEN-001",
        item_name="Pluma azul",
        presentation_id=None,
        presentation_name="Caja 12",
        barcode="750000000001",
        conversion_factor=Decimal("12.000"),
        quantity=Decimal("2.000"),
        unit_price=Decimal("35.00"),
        line_subtotal=Decimal("70.00"),
        discount_amount=Decimal("5.00"),
        line_total=Decimal("65.00"),
        unit_cost_snapshot=Decimal("18.00"),
    )

    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)

    assert line.sale_id == sale.id
    assert line.item_type == "PRODUCT"
    assert line.item_name == "Pluma azul"
    assert line.presentation_name == "Caja 12"
    assert line.quantity == Decimal("2.000")
    assert line.line_total == Decimal("65.00")


@pytest.mark.parametrize(
    "method",
    [
        "CASH",
        "CARD",
    ],
)
def test_payment_accepts_cash_and_card(
    db_session,
    method,
):
    branch = _branch(
        db_session,
        f"payment-{method.lower()}",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name=f"{method} Cashier",
    )
    sale = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid=f"sale-{method}",
        status="PAID",
    )

    payment = RetailPayment(
        sale_id=sale.id,
        payment_uuid=f"payment-{method}",
        method=method,
        amount=Decimal("90.00"),
        amount_tendered=(
            Decimal("100.00")
            if method == "CASH"
            else None
        ),
        change_due=(
            Decimal("10.00")
            if method == "CASH"
            else Decimal("0.00")
        ),
        external_reference=(
            "CARD-REF-123"
            if method == "CARD"
            else None
        ),
    )

    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    assert payment.id is not None
    assert payment.method == method


def test_payment_rejects_unknown_method(
    db_session,
):
    branch = _branch(
        db_session,
        "payment-invalid",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Payment Invalid Cashier",
    )
    sale = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="sale-invalid-payment",
        status="PAID",
    )

    payment = RetailPayment(
        sale_id=sale.id,
        payment_uuid="payment-invalid",
        method="TRANSFER",
        amount=Decimal("90.00"),
        change_due=Decimal("0.00"),
    )

    db_session.add(payment)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_payment_uuid_is_unique(
    db_session,
):
    branch = _branch(
        db_session,
        "payment-uuid",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Payment UUID Cashier",
    )

    sale_a = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="payment-sale-a",
        status="PAID",
    )

    sale_b = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="payment-sale-b",
        status="PAID",
    )

    first = RetailPayment(
        sale_id=sale_a.id,
        payment_uuid="same-payment-uuid",
        method="CARD",
        amount=Decimal("90.00"),
        change_due=Decimal("0.00"),
    )
    db_session.add(first)
    db_session.commit()

    second = RetailPayment(
        sale_id=sale_b.id,
        payment_uuid="same-payment-uuid",
        method="CARD",
        amount=Decimal("90.00"),
        change_due=Decimal("0.00"),
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_return_and_return_line_reference_original_sale(
    db_session,
):
    branch = _branch(
        db_session,
        "return-model",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Return Cashier",
    )

    sale = _sale(
        db_session,
        branch=branch,
        staff=staff,
        sale_uuid="return-original",
        status="PAID",
    )

    sale_line = RetailSaleLine(
        sale_id=sale.id,
        item_type="PRODUCT",
        sku="RETURN-001",
        item_name="Cuaderno",
        presentation_name="Pieza",
        conversion_factor=Decimal("1.000"),
        quantity=Decimal("2.000"),
        unit_price=Decimal("50.00"),
        line_subtotal=Decimal("100.00"),
        discount_amount=Decimal("10.00"),
        line_total=Decimal("90.00"),
        unit_cost_snapshot=Decimal("30.00"),
    )

    db_session.add(sale_line)
    db_session.flush()

    retail_return = RetailReturn(
        return_uuid="return-uuid-1",
        sale_id=sale.id,
        cashier_staff_id=staff.id,
        authorizer_staff_id=staff.id,
        reason="Cliente devolvió una pieza",
        subtotal=Decimal("50.00"),
        total=Decimal("45.00"),
    )

    db_session.add(retail_return)
    db_session.flush()

    return_line = RetailReturnLine(
        return_id=retail_return.id,
        sale_line_id=sale_line.id,
        quantity=Decimal("1.000"),
        unit_amount=Decimal("45.00"),
        line_total=Decimal("45.00"),
    )

    db_session.add(return_line)
    db_session.commit()

    assert retail_return.sale_id == sale.id
    assert return_line.sale_line_id == sale_line.id
    assert return_line.return_id == retail_return.id


def test_paid_sale_can_store_receipt_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "receipt-snapshot",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Receipt Cashier",
    )

    sale = RetailSale(
        sale_uuid="receipt-sale",
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T1",
        cashier_staff_id=staff.id,
        status="PAID",
        subtotal=Decimal("100.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("100.00"),
        currency="MXN",
        receipt_snapshot={
            "folio": "receipt-sale",
            "total": "100.00",
            "cashier": "Receipt Cashier",
        },
    )

    db_session.add(sale)
    db_session.commit()
    db_session.refresh(sale)

    assert sale.receipt_snapshot["folio"] == "receipt-sale"
    assert sale.receipt_snapshot["total"] == "100.00"


def test_held_sale_rejects_receipt_snapshot(
    db_session,
):
    branch = _branch(
        db_session,
        "held-receipt-invalid",
    )
    staff = _staff(
        db_session,
        branch=branch,
        name="Held Receipt Cashier",
    )

    sale = RetailSale(
        sale_uuid="held-with-receipt",
        branch_id=branch.id,
        module_code="PAPELERIA",
        terminal_id="T1",
        cashier_staff_id=staff.id,
        status="HELD",
        subtotal=Decimal("10.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("10.00"),
        currency="MXN",
        receipt_snapshot={
            "folio": "not-allowed-yet",
        },
    )

    db_session.add(sale)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
