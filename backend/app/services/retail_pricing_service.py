from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from fastapi import HTTPException, status
from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
    RetailServicePriceTier,
)
from app.schemas.retail_catalog import (
    RetailPriceQuote,
)


MONEY_QUANTUM = Decimal("0.01")


class RetailPricingService:
    @staticmethod
    def _quantity(
        quantity: Decimal,
    ) -> Decimal:
        try:
            normalized = Decimal(
                str(quantity)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="Invalid retail quantity",
            ) from exc

        if (
            not normalized.is_finite()
            or normalized <= Decimal("0")
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Retail quantity must be positive"
                ),
            )

        return normalized

    @staticmethod
    def _money(
        value: Decimal,
    ) -> Decimal:
        return Decimal(
            value
        ).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def quote(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
        quantity: Decimal,
        presentation_id: int | None = None,
    ) -> RetailPriceQuote:
        normalized_quantity = cls._quantity(
            quantity
        )

        if not item.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Retail item is inactive",
            )

        if item.item_type == "PRODUCT":
            return cls._quote_product(
                db,
                item=item,
                quantity=normalized_quantity,
                presentation_id=presentation_id,
            )

        if item.item_type == "SERVICE":
            return cls._quote_service(
                db,
                item=item,
                quantity=normalized_quantity,
                presentation_id=presentation_id,
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid retail item type",
        )

    @classmethod
    def _quote_product(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
        quantity: Decimal,
        presentation_id: int | None,
    ) -> RetailPriceQuote:
        query = select(
            RetailPresentation
        ).where(
            RetailPresentation.item_id
            == item.id,
            RetailPresentation.branch_id
            == item.branch_id,
            RetailPresentation.is_active.is_(
                True
            ),
        )

        if presentation_id is None:
            query = query.where(
                RetailPresentation.is_default.is_(
                    True
                )
            )
        else:
            query = query.where(
                RetailPresentation.id
                == presentation_id
            )

        presentation = db.execute(
            query.order_by(
                RetailPresentation.id.asc()
            ).limit(1)
        ).scalar_one_or_none()

        if presentation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Retail presentation not found"
                ),
            )

        use_bulk = (
            presentation.bulk_price
            is not None
            and presentation.bulk_min_quantity
            is not None
            and quantity
            >= Decimal(
                presentation.bulk_min_quantity
            )
        )

        if use_bulk:
            unit_price = cls._money(
                Decimal(
                    presentation.bulk_price
                )
            )
            pricing_rule = "BULK_PRICE"
        else:
            unit_price = cls._money(
                Decimal(
                    presentation.sale_price
                )
            )
            pricing_rule = "SALE_PRICE"

        line_total = cls._money(
            unit_price * quantity
        )

        return RetailPriceQuote(
            unit_price=unit_price,
            line_total=line_total,
            pricing_rule=pricing_rule,
        )

    @classmethod
    def _quote_service(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
        quantity: Decimal,
        presentation_id: int | None,
    ) -> RetailPriceQuote:
        if presentation_id is not None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Services do not use presentations"
                ),
            )

        matching_tiers = (
            db.execute(
                select(
                    RetailServicePriceTier
                )
                .where(
                    RetailServicePriceTier.item_id
                    == item.id,
                    RetailServicePriceTier.min_quantity
                    <= quantity,
                    or_(
                        RetailServicePriceTier.max_quantity
                        .is_(None),
                        RetailServicePriceTier.max_quantity
                        >= quantity,
                    ),
                )
                .order_by(
                    RetailServicePriceTier
                    .min_quantity.desc(),
                    RetailServicePriceTier.id.asc(),
                )
            )
            .scalars()
            .all()
        )

        if not matching_tiers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No service price tier "
                    "matches quantity"
                ),
            )

        if len(matching_tiers) != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Overlapping service price tiers"
                ),
            )

        tier = matching_tiers[0]

        unit_price = cls._money(
            Decimal(
                tier.unit_price
            )
        )

        line_total = cls._money(
            unit_price * quantity
        )

        return RetailPriceQuote(
            unit_price=unit_price,
            line_total=line_total,
            pricing_rule="SERVICE_TIER",
        )
