from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
    RetailServicePriceTier,
)


def _branch(
    db_session,
    *,
    code: str,
    name: str,
) -> Branch:
    branch = Branch(
        code=code,
        name=name,
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
    sku: str = "PAPER-LETTER",
    name: str = "Papel carta",
    is_active: bool = True,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=name,
        description="Papel blanco tamaño carta",
        category="Papelería",
        base_unit_code="PIECE",
        cost=Decimal("1.250"),
        inventory_tracked=True,
        low_stock_threshold=Decimal("10.000"),
        max_stock=Decimal("500.000"),
        is_active=is_active,
    )

    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    return item


def _service(
    db_session,
    *,
    branch: Branch,
    sku: str = "COPY-BW",
    name: str = "Copia B/N",
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="SERVICE",
        sku=sku,
        name=name,
        description="Copia blanco y negro tamaño carta",
        category="Copias e impresiones",
        base_unit_code="SERVICE",
        cost=Decimal("0.00"),
        inventory_tracked=False,
        low_stock_threshold=None,
        max_stock=None,
        is_active=True,
    )

    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    return item


def test_product_supports_piece_and_box_presentations(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-a",
        name="Retail A",
    )

    product = _product(
        db_session,
        branch=branch,
    )

    piece = RetailPresentation(
        item_id=product.id,
        branch_id=branch.id,
        name="Pieza",
        barcode="750000000001",
        conversion_factor=Decimal("1.000"),
        sale_price=Decimal("3.50"),
        bulk_price=None,
        bulk_min_quantity=None,
        is_default=True,
        is_active=True,
    )

    box = RetailPresentation(
        item_id=product.id,
        branch_id=branch.id,
        name="Caja 12",
        barcode="750000000012",
        conversion_factor=Decimal("12.000"),
        sale_price=Decimal("38.00"),
        bulk_price=Decimal("35.00"),
        bulk_min_quantity=Decimal("3.000"),
        is_default=False,
        is_active=True,
    )

    db_session.add_all(
        [
            piece,
            box,
        ]
    )
    db_session.commit()

    db_session.refresh(product)

    presentations = {
        presentation.name: presentation
        for presentation in product.presentations
    }

    assert set(presentations) == {
        "Pieza",
        "Caja 12",
    }

    assert (
        presentations["Pieza"].conversion_factor
        == Decimal("1.000")
    )

    assert (
        presentations["Caja 12"].conversion_factor
        == Decimal("12.000")
    )

    assert (
        presentations["Caja 12"].bulk_price
        == Decimal("35.00")
    )

    assert (
        presentations["Caja 12"].bulk_min_quantity
        == Decimal("3.000")
    )


def test_barcode_is_unique_within_branch(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-unique",
        name="Retail Unique",
    )

    product_a = _product(
        db_session,
        branch=branch,
        sku="PRODUCT-A",
        name="Producto A",
    )

    product_b = _product(
        db_session,
        branch=branch,
        sku="PRODUCT-B",
        name="Producto B",
    )

    db_session.add(
        RetailPresentation(
            item_id=product_a.id,
            branch_id=branch.id,
            name="Pieza A",
            barcode="7501234567890",
            conversion_factor=Decimal("1.000"),
            sale_price=Decimal("10.00"),
            is_default=True,
            is_active=True,
        )
    )

    db_session.commit()

    db_session.add(
        RetailPresentation(
            item_id=product_b.id,
            branch_id=branch.id,
            name="Pieza B",
            barcode="7501234567890",
            conversion_factor=Decimal("1.000"),
            sale_price=Decimal("20.00"),
            is_default=True,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_same_barcode_is_allowed_in_different_branches(
    db_session,
):
    branch_a = _branch(
        db_session,
        code="retail-branch-a",
        name="Retail Branch A",
    )

    branch_b = _branch(
        db_session,
        code="retail-branch-b",
        name="Retail Branch B",
    )

    product_a = _product(
        db_session,
        branch=branch_a,
        sku="A-001",
        name="Producto A",
    )

    product_b = _product(
        db_session,
        branch=branch_b,
        sku="B-001",
        name="Producto B",
    )

    barcode = "7509999999999"

    presentation_a = RetailPresentation(
        item_id=product_a.id,
        branch_id=branch_a.id,
        name="Pieza",
        barcode=barcode,
        conversion_factor=Decimal("1.000"),
        sale_price=Decimal("15.00"),
        is_default=True,
        is_active=True,
    )

    presentation_b = RetailPresentation(
        item_id=product_b.id,
        branch_id=branch_b.id,
        name="Pieza",
        barcode=barcode,
        conversion_factor=Decimal("1.000"),
        sale_price=Decimal("18.00"),
        is_default=True,
        is_active=True,
    )

    db_session.add_all(
        [
            presentation_a,
            presentation_b,
        ]
    )

    db_session.commit()

    assert presentation_a.id is not None
    assert presentation_b.id is not None


def test_null_barcode_can_repeat_within_branch(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-null-barcode",
        name="Retail Null Barcode",
    )

    product_a = _product(
        db_session,
        branch=branch,
        sku="NULL-A",
        name="Producto Null A",
    )

    product_b = _product(
        db_session,
        branch=branch,
        sku="NULL-B",
        name="Producto Null B",
    )

    db_session.add_all(
        [
            RetailPresentation(
                item_id=product_a.id,
                branch_id=branch.id,
                name="Sin código A",
                barcode=None,
                conversion_factor=Decimal("1.000"),
                sale_price=Decimal("5.00"),
                is_default=True,
                is_active=True,
            ),
            RetailPresentation(
                item_id=product_b.id,
                branch_id=branch.id,
                name="Sin código B",
                barcode=None,
                conversion_factor=Decimal("1.000"),
                sale_price=Decimal("7.00"),
                is_default=True,
                is_active=True,
            ),
        ]
    )

    db_session.commit()


def test_service_can_exist_without_presentations(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-services",
        name="Retail Services",
    )

    service = _service(
        db_session,
        branch=branch,
    )

    db_session.refresh(service)

    assert service.item_type == "SERVICE"
    assert service.inventory_tracked is False
    assert service.presentations == []


@pytest.mark.parametrize(
    "conversion_factor",
    [
        Decimal("0.000"),
        Decimal("-1.000"),
    ],
)
def test_presentation_rejects_zero_or_negative_conversion_factor(
    db_session,
    conversion_factor,
):
    branch = _branch(
        db_session,
        code=(
            "retail-conversion-"
            + str(conversion_factor).replace("-", "neg")
        ),
        name="Retail Conversion",
    )

    product = _product(
        db_session,
        branch=branch,
    )

    presentation = RetailPresentation(
        item_id=product.id,
        branch_id=branch.id,
        name="Inválida",
        barcode=None,
        conversion_factor=conversion_factor,
        sale_price=Decimal("10.00"),
        is_default=True,
        is_active=True,
    )

    db_session.add(presentation)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_service_supports_quantity_price_tiers(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-tier-service",
        name="Retail Tier Service",
    )

    service = _service(
        db_session,
        branch=branch,
    )

    tier_1 = RetailServicePriceTier(
        item_id=service.id,
        min_quantity=Decimal("1.000"),
        max_quantity=Decimal("20.000"),
        unit_price=Decimal("2.00"),
    )

    tier_2 = RetailServicePriceTier(
        item_id=service.id,
        min_quantity=Decimal("21.000"),
        max_quantity=Decimal("100.000"),
        unit_price=Decimal("1.50"),
    )

    tier_3 = RetailServicePriceTier(
        item_id=service.id,
        min_quantity=Decimal("101.000"),
        max_quantity=None,
        unit_price=Decimal("1.00"),
    )

    db_session.add_all(
        [
            tier_1,
            tier_2,
            tier_3,
        ]
    )

    db_session.commit()
    db_session.refresh(service)

    assert len(service.service_price_tiers) == 3

    assert (
        service.service_price_tiers[0].min_quantity
        == Decimal("1.000")
    )

    assert (
        service.service_price_tiers[-1].max_quantity
        is None
    )


def test_inactive_item_state_is_persisted(
    db_session,
):
    branch = _branch(
        db_session,
        code="retail-inactive",
        name="Retail Inactive",
    )

    product = _product(
        db_session,
        branch=branch,
        sku="INACTIVE-001",
        name="Producto inactivo",
        is_active=False,
    )

    db_session.expire_all()

    loaded = db_session.get(
        RetailCatalogItem,
        product.id,
    )

    assert loaded is not None
    assert loaded.is_active is False
