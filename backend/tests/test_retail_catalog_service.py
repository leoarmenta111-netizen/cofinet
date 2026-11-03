from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.retail_catalog import RetailCatalogItem
from app.services.retail_catalog_service import RetailCatalogService


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


def _item(
    db_session,
    *,
    branch: Branch,
    item_type: str,
    sku: str,
) -> RetailCatalogItem:
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type=item_type,
        sku=sku,
        name=sku,
        description=None,
        category="Test",
        base_unit_code=(
            "PIECE"
            if item_type == "PRODUCT"
            else "SERVICE"
        ),
        cost=Decimal("0.00"),
        inventory_tracked=(
            item_type == "PRODUCT"
        ),
        low_stock_threshold=None,
        max_stock=None,
        is_active=True,
    )

    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    return item


def test_product_can_receive_presentation(
    db_session,
):
    branch = _branch(
        db_session,
        "catalog-service-product",
    )

    product = _item(
        db_session,
        branch=branch,
        item_type="PRODUCT",
        sku="PRODUCT-001",
    )

    presentation = (
        RetailCatalogService.create_presentation(
            db_session,
            item=product,
            branch_id=branch.id,
            name="Pieza",
            barcode="750100000001",
            conversion_factor=Decimal("1.000"),
            sale_price=Decimal("10.00"),
            bulk_price=None,
            bulk_min_quantity=None,
            is_default=True,
            is_active=True,
        )
    )

    db_session.commit()

    assert presentation.id is not None
    assert presentation.item_id == product.id


def test_service_cannot_receive_presentation(
    db_session,
):
    branch = _branch(
        db_session,
        "catalog-service-no-presentation",
    )

    service = _item(
        db_session,
        branch=branch,
        item_type="SERVICE",
        sku="SERVICE-001",
    )

    with pytest.raises(HTTPException) as exc:
        RetailCatalogService.create_presentation(
            db_session,
            item=service,
            branch_id=branch.id,
            name="No permitido",
            barcode=None,
            conversion_factor=Decimal("1.000"),
            sale_price=Decimal("10.00"),
            bulk_price=None,
            bulk_min_quantity=None,
            is_default=True,
            is_active=True,
        )

    assert exc.value.status_code == 422


def test_service_can_receive_price_tier(
    db_session,
):
    branch = _branch(
        db_session,
        "catalog-service-tier",
    )

    service = _item(
        db_session,
        branch=branch,
        item_type="SERVICE",
        sku="SERVICE-002",
    )

    tier = (
        RetailCatalogService.create_service_price_tier(
            db_session,
            item=service,
            min_quantity=Decimal("1.000"),
            max_quantity=Decimal("20.000"),
            unit_price=Decimal("2.00"),
        )
    )

    db_session.commit()

    assert tier.id is not None
    assert tier.item_id == service.id


def test_product_cannot_receive_service_price_tier(
    db_session,
):
    branch = _branch(
        db_session,
        "catalog-product-no-tier",
    )

    product = _item(
        db_session,
        branch=branch,
        item_type="PRODUCT",
        sku="PRODUCT-002",
    )

    with pytest.raises(HTTPException) as exc:
        RetailCatalogService.create_service_price_tier(
            db_session,
            item=product,
            min_quantity=Decimal("1.000"),
            max_quantity=Decimal("20.000"),
            unit_price=Decimal("2.00"),
        )

    assert exc.value.status_code == 422


def test_presentation_branch_must_match_item_branch(
    db_session,
):
    branch_a = _branch(
        db_session,
        "catalog-branch-a",
    )

    branch_b = _branch(
        db_session,
        "catalog-branch-b",
    )

    product = _item(
        db_session,
        branch=branch_a,
        item_type="PRODUCT",
        sku="PRODUCT-003",
    )

    with pytest.raises(HTTPException) as exc:
        RetailCatalogService.create_presentation(
            db_session,
            item=product,
            branch_id=branch_b.id,
            name="Pieza",
            barcode="750100000003",
            conversion_factor=Decimal("1.000"),
            sale_price=Decimal("10.00"),
            bulk_price=None,
            bulk_min_quantity=None,
            is_default=True,
            is_active=True,
        )

    assert exc.value.status_code == 422
