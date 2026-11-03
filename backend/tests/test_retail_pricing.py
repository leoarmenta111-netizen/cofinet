from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
    RetailServicePriceTier,
)
from app.services.retail_pricing_service import (
    RetailPricingService,
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
) -> tuple[
    RetailCatalogItem,
    RetailPresentation,
]:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku="PEN-BLUE",
        name="Pluma azul",
        category="Escritura",
        base_unit_code="PIECE",
        cost=Decimal("3.00"),
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
        barcode="750000009999",
        conversion_factor=Decimal("1.000"),
        sale_price=Decimal("10.00"),
        bulk_price=Decimal("8.50"),
        bulk_min_quantity=Decimal("10.000"),
        is_default=True,
        is_active=True,
    )

    db_session.add(presentation)
    db_session.commit()

    db_session.refresh(item)
    db_session.refresh(presentation)

    return item, presentation


def _service(
    db_session,
    *,
    branch: Branch,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="SERVICE",
        sku="COPY-BW",
        name="Copia blanco y negro",
        category="Copias",
        base_unit_code="SERVICE",
        cost=Decimal("0.00"),
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


def test_product_uses_sale_price_before_bulk_threshold(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-product-normal",
    )

    item, presentation = _product(
        db_session,
        branch=branch,
    )

    quote = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("9.000"),
        presentation_id=presentation.id,
    )

    assert quote.unit_price == Decimal("10.00")
    assert quote.line_total == Decimal("90.00")
    assert quote.pricing_rule == "SALE_PRICE"


def test_product_uses_bulk_price_at_threshold(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-product-bulk",
    )

    item, presentation = _product(
        db_session,
        branch=branch,
    )

    quote = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("10.000"),
        presentation_id=presentation.id,
    )

    assert quote.unit_price == Decimal("8.50")
    assert quote.line_total == Decimal("85.00")
    assert quote.pricing_rule == "BULK_PRICE"


def test_product_uses_default_presentation_when_id_is_omitted(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-product-default",
    )

    item, _ = _product(
        db_session,
        branch=branch,
    )

    quote = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("2.000"),
    )

    assert quote.unit_price == Decimal("10.00")
    assert quote.line_total == Decimal("20.00")
    assert quote.pricing_rule == "SALE_PRICE"


def test_service_tier_boundary_20_and_21(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-service-boundary",
    )

    item = _service(
        db_session,
        branch=branch,
    )

    quote_20 = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("20.000"),
    )

    quote_21 = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("21.000"),
    )

    assert quote_20.unit_price == Decimal("2.00")
    assert quote_20.line_total == Decimal("40.00")
    assert quote_20.pricing_rule == "SERVICE_TIER"

    assert quote_21.unit_price == Decimal("1.50")
    assert quote_21.line_total == Decimal("31.50")
    assert quote_21.pricing_rule == "SERVICE_TIER"


def test_service_uses_open_ended_final_tier(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-service-open",
    )

    item = _service(
        db_session,
        branch=branch,
    )

    quote = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("150.000"),
    )

    assert quote.unit_price == Decimal("1.00")
    assert quote.line_total == Decimal("150.00")
    assert quote.pricing_rule == "SERVICE_TIER"


def test_quote_accepts_positive_decimal_quantity_without_float_rounding(
    db_session,
):
    branch = _branch(
        db_session,
        "pricing-decimal",
    )

    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="SERVICE",
        sku="SCAN-DECIMAL",
        name="Servicio decimal",
        category="Servicios",
        base_unit_code="SERVICE",
        cost=Decimal("0.00"),
        inventory_tracked=False,
        is_active=True,
    )

    db_session.add(item)
    db_session.flush()

    db_session.add(
        RetailServicePriceTier(
            item_id=item.id,
            min_quantity=Decimal("0.001"),
            max_quantity=None,
            unit_price=Decimal("0.10"),
        )
    )

    db_session.commit()
    db_session.refresh(item)

    quote = RetailPricingService.quote(
        db_session,
        item=item,
        quantity=Decimal("0.300"),
    )

    assert quote.unit_price == Decimal("0.10")
    assert quote.line_total == Decimal("0.03")
    assert isinstance(quote.line_total, Decimal)


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-0.001"),
    ],
)
def test_quote_rejects_zero_or_negative_quantity(
    db_session,
    quantity,
):
    branch = _branch(
        db_session,
        (
            "pricing-invalid-"
            + str(abs(quantity)).replace(".", "-")
        ),
    )

    item, presentation = _product(
        db_session,
        branch=branch,
    )

    with pytest.raises(HTTPException) as exc:
        RetailPricingService.quote(
            db_session,
            item=item,
            quantity=quantity,
            presentation_id=presentation.id,
        )

    assert exc.value.status_code == 422
