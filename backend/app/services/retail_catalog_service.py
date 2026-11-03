from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
    RetailServicePriceTier,
)


class RetailCatalogService:
    @staticmethod
    def create_presentation(
        db: Session,
        *,
        item: RetailCatalogItem,
        branch_id: int,
        name: str,
        barcode: str | None,
        conversion_factor: Decimal,
        sale_price: Decimal,
        bulk_price: Decimal | None,
        bulk_min_quantity: Decimal | None,
        is_default: bool,
        is_active: bool,
    ) -> RetailPresentation:
        if item.item_type != "PRODUCT":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Presentations are allowed only "
                    "for PRODUCT items"
                ),
            )

        if item.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Presentation branch must match "
                    "item branch"
                ),
            )

        factor = Decimal(str(conversion_factor))

        if (
            not factor.is_finite()
            or factor <= Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Conversion factor must be positive"
                ),
            )

        price = Decimal(str(sale_price))

        if (
            not price.is_finite()
            or price < Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Sale price cannot be negative",
            )

        normalized_bulk_price = (
            Decimal(str(bulk_price))
            if bulk_price is not None
            else None
        )

        normalized_bulk_min = (
            Decimal(str(bulk_min_quantity))
            if bulk_min_quantity is not None
            else None
        )

        if (
            (normalized_bulk_price is None)
            != (normalized_bulk_min is None)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Bulk price and threshold "
                    "must be provided together"
                ),
            )

        if (
            normalized_bulk_price is not None
            and (
                not normalized_bulk_price.is_finite()
                or normalized_bulk_price
                < Decimal("0")
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Bulk price cannot be negative"
                ),
            )

        if (
            normalized_bulk_min is not None
            and (
                not normalized_bulk_min.is_finite()
                or normalized_bulk_min
                <= Decimal("0")
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Bulk minimum quantity "
                    "must be positive"
                ),
            )

        presentation = RetailPresentation(
            item_id=item.id,
            branch_id=branch_id,
            name=name.strip(),
            barcode=(
                barcode.strip()
                if barcode is not None
                and barcode.strip()
                else None
            ),
            conversion_factor=factor,
            sale_price=price,
            bulk_price=normalized_bulk_price,
            bulk_min_quantity=normalized_bulk_min,
            is_default=is_default,
            is_active=is_active,
        )

        db.add(presentation)
        db.flush()

        return presentation

    @staticmethod
    def create_service_price_tier(
        db: Session,
        *,
        item: RetailCatalogItem,
        min_quantity: Decimal,
        max_quantity: Decimal | None,
        unit_price: Decimal,
    ) -> RetailServicePriceTier:
        if item.item_type != "SERVICE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Price tiers are allowed only "
                    "for SERVICE items"
                ),
            )

        minimum = Decimal(str(min_quantity))

        maximum = (
            Decimal(str(max_quantity))
            if max_quantity is not None
            else None
        )

        price = Decimal(str(unit_price))

        if (
            not minimum.is_finite()
            or minimum <= Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Minimum quantity must be positive"
                ),
            )

        if (
            maximum is not None
            and (
                not maximum.is_finite()
                or maximum < minimum
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid service tier range",
            )

        if (
            not price.is_finite()
            or price < Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unit price cannot be negative",
            )

        tier = RetailServicePriceTier(
            item_id=item.id,
            min_quantity=minimum,
            max_quantity=maximum,
            unit_price=price,
        )

        db.add(tier)
        db.flush()

        return tier
