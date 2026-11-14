from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
)
from app.services.retail_catalog_service import (
    RetailCatalogService,
)


ZERO = Decimal("0.000")


class AdminRetailCatalogService:
    @staticmethod
    def _money(
        value: Decimal,
    ) -> Decimal:
        normalized = Decimal(str(value))

        if (
            not normalized.is_finite()
            or normalized < Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid monetary value",
            )

        return normalized

    @staticmethod
    def _quantity(
        value: Decimal | None,
    ) -> Decimal | None:
        if value is None:
            return None

        normalized = Decimal(str(value))

        if (
            not normalized.is_finite()
            or normalized < ZERO
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid stock quantity",
            )

        return normalized

    @classmethod
    def _validate_stock_limits(
        cls,
        *,
        low_stock_threshold: Decimal | None,
        max_stock: Decimal | None,
    ) -> tuple[
        Decimal | None,
        Decimal | None,
    ]:
        low = cls._quantity(
            low_stock_threshold
        )
        maximum = cls._quantity(
            max_stock
        )

        if (
            low is not None
            and maximum is not None
            and low > maximum
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Low stock threshold cannot "
                    "exceed max stock"
                ),
            )

        return low, maximum

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be empty",
            )

        return normalized

    @staticmethod
    def _assert_product_inventory_rules(
        *,
        item_type: str,
        inventory_tracked: bool,
        low_stock_threshold: Decimal | None,
        max_stock: Decimal | None,
    ) -> None:
        if (
            item_type == "SERVICE"
            and (
                inventory_tracked
                or low_stock_threshold is not None
                or max_stock is not None
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Services cannot use "
                    "inventory settings"
                ),
            )

    @staticmethod
    def _assert_sku_available(
        db: Session,
        *,
        branch_id: int,
        sku: str | None,
        exclude_item_id: int | None = None,
    ) -> None:
        if sku is None:
            return

        statement = select(
            RetailCatalogItem.id
        ).where(
            RetailCatalogItem.branch_id
            == branch_id,
            RetailCatalogItem.sku == sku,
        )

        if exclude_item_id is not None:
            statement = statement.where(
                RetailCatalogItem.id
                != exclude_item_id
            )

        existing = db.execute(
            statement
        ).scalar_one_or_none()

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Retail SKU already exists "
                    "for this branch"
                ),
            )

    @staticmethod
    def _assert_barcode_available(
        db: Session,
        *,
        branch_id: int,
        barcode: str | None,
        exclude_presentation_id: (
            int | None
        ) = None,
    ) -> None:
        if barcode is None:
            return

        statement = select(
            RetailPresentation.id
        ).where(
            RetailPresentation.branch_id
            == branch_id,
            RetailPresentation.barcode
            == barcode,
        )

        if exclude_presentation_id is not None:
            statement = statement.where(
                RetailPresentation.id
                != exclude_presentation_id
            )

        existing = db.execute(
            statement
        ).scalar_one_or_none()

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Retail barcode already exists "
                    "for this branch"
                ),
            )

    @staticmethod
    def _inventory_balance(
        db: Session,
        *,
        item: RetailCatalogItem,
    ) -> RetailInventoryBalance | None:
        return db.execute(
            select(
                RetailInventoryBalance
            ).where(
                RetailInventoryBalance.branch_id
                == item.branch_id,
                RetailInventoryBalance.item_id
                == item.id,
            )
        ).scalar_one_or_none()

    @classmethod
    def _sync_inventory_balance(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
    ) -> RetailInventoryBalance | None:
        balance = cls._inventory_balance(
            db,
            item=item,
        )

        if (
            balance is None
            and item.item_type == "PRODUCT"
            and item.inventory_tracked
        ):
            balance = RetailInventoryBalance(
                branch_id=item.branch_id,
                item_id=item.id,
                quantity_on_hand=ZERO,
                low_stock_threshold=(
                    item.low_stock_threshold
                ),
                max_stock=item.max_stock,
            )

            db.add(balance)
            db.flush()

            return balance

        if balance is not None:
            balance.low_stock_threshold = (
                item.low_stock_threshold
            )
            balance.max_stock = item.max_stock
            db.flush()

        return balance

    @staticmethod
    def list_catalog(
        db: Session,
        *,
        branch_id: int,
    ) -> list[RetailCatalogItem]:
        return list(
            db.execute(
                select(RetailCatalogItem)
                .options(
                    selectinload(
                        RetailCatalogItem.presentations
                    ),
                    selectinload(
                        RetailCatalogItem
                        .service_price_tiers
                    ),
                )
                .where(
                    RetailCatalogItem.branch_id
                    == branch_id
                )
                .order_by(
                    RetailCatalogItem.name,
                    RetailCatalogItem.id,
                )
            )
            .scalars()
            .unique()
            .all()
        )

    @staticmethod
    def get_item(
        db: Session,
        *,
        item_id: int,
        branch_id: int | None = None,
    ) -> RetailCatalogItem:
        statement = select(
            RetailCatalogItem
        ).where(
            RetailCatalogItem.id
            == item_id
        )

        if branch_id is not None:
            statement = statement.where(
                RetailCatalogItem.branch_id
                == branch_id
            )

        item = db.execute(
            statement
        ).scalar_one_or_none()

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retail catalog item not found",
            )

        return item

    @classmethod
    def create_item(
        cls,
        db: Session,
        *,
        branch_id: int,
        item_type: str,
        sku: str | None,
        name: str,
        description: str | None,
        category: str | None,
        base_unit_code: str,
        cost: Decimal,
        inventory_tracked: bool,
        low_stock_threshold: Decimal | None,
        max_stock: Decimal | None,
        is_active: bool,
    ) -> RetailCatalogItem:
        normalized_sku = (
            cls._normalize_optional_text(sku)
        )

        normalized_name = (
            cls._normalize_required_text(
                name,
                field="Name",
            )
        )

        normalized_unit = (
            cls._normalize_required_text(
                base_unit_code,
                field="Base unit code",
            )
        )

        low, maximum = (
            cls._validate_stock_limits(
                low_stock_threshold=(
                    low_stock_threshold
                ),
                max_stock=max_stock,
            )
        )

        cls._assert_product_inventory_rules(
            item_type=item_type,
            inventory_tracked=inventory_tracked,
            low_stock_threshold=low,
            max_stock=maximum,
        )

        cls._assert_sku_available(
            db,
            branch_id=branch_id,
            sku=normalized_sku,
        )

        item = RetailCatalogItem(
            branch_id=branch_id,
            item_type=item_type,
            sku=normalized_sku,
            name=normalized_name,
            description=(
                cls._normalize_optional_text(
                    description
                )
            ),
            category=(
                cls._normalize_optional_text(
                    category
                )
            ),
            base_unit_code=normalized_unit,
            cost=cls._money(cost),
            inventory_tracked=inventory_tracked,
            low_stock_threshold=low,
            max_stock=maximum,
            is_active=is_active,
        )

        db.add(item)
        db.flush()

        cls._sync_inventory_balance(
            db,
            item=item,
        )

        return item

    @classmethod
    def update_item(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
        changes: dict[str, object],
    ) -> RetailCatalogItem:
        if "sku" in changes:
            sku_value = changes["sku"]

            if (
                sku_value is not None
                and not isinstance(
                    sku_value,
                    str,
                )
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid SKU",
                )

            normalized_sku = (
                cls._normalize_optional_text(
                    sku_value
                )
            )

            cls._assert_sku_available(
                db,
                branch_id=item.branch_id,
                sku=normalized_sku,
                exclude_item_id=item.id,
            )

            item.sku = normalized_sku

        if "name" in changes:
            value = changes["name"]

            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Name is required",
                )

            item.name = (
                cls._normalize_required_text(
                    value,
                    field="Name",
                )
            )

        if "description" in changes:
            value = changes["description"]

            if (
                value is not None
                and not isinstance(value, str)
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid description",
                )

            item.description = (
                cls._normalize_optional_text(
                    value
                )
            )

        if "category" in changes:
            value = changes["category"]

            if (
                value is not None
                and not isinstance(value, str)
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid category",
                )

            item.category = (
                cls._normalize_optional_text(
                    value
                )
            )

        if "base_unit_code" in changes:
            value = changes[
                "base_unit_code"
            ]

            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Base unit code is required",
                )

            item.base_unit_code = (
                cls._normalize_required_text(
                    value,
                    field="Base unit code",
                )
            )

        if "cost" in changes:
            value = changes["cost"]

            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cost cannot be null",
                )

            item.cost = cls._money(value)

        inventory_tracked = (
            changes.get(
                "inventory_tracked",
                item.inventory_tracked,
            )
        )

        if inventory_tracked is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Inventory tracked "
                    "cannot be null"
                ),
            )

        low = (
            changes["low_stock_threshold"]
            if "low_stock_threshold" in changes
            else item.low_stock_threshold
        )

        maximum = (
            changes["max_stock"]
            if "max_stock" in changes
            else item.max_stock
        )

        low, maximum = (
            cls._validate_stock_limits(
                low_stock_threshold=low,
                max_stock=maximum,
            )
        )

        cls._assert_product_inventory_rules(
            item_type=item.item_type,
            inventory_tracked=bool(
                inventory_tracked
            ),
            low_stock_threshold=low,
            max_stock=maximum,
        )

        item.inventory_tracked = bool(
            inventory_tracked
        )
        item.low_stock_threshold = low
        item.max_stock = maximum

        if "is_active" in changes:
            value = changes["is_active"]

            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Active flag cannot be null"
                    ),
                )

            item.is_active = bool(value)

        db.flush()

        cls._sync_inventory_balance(
            db,
            item=item,
        )

        return item

    @staticmethod
    def get_presentation(
        db: Session,
        *,
        presentation_id: int,
    ) -> RetailPresentation:
        presentation = db.get(
            RetailPresentation,
            presentation_id,
        )

        if presentation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Retail presentation not found"
                ),
            )

        return presentation

    @staticmethod
    def _unset_other_defaults(
        db: Session,
        *,
        item_id: int,
        exclude_presentation_id: (
            int | None
        ) = None,
    ) -> None:
        presentations = db.execute(
            select(
                RetailPresentation
            ).where(
                RetailPresentation.item_id
                == item_id,
                RetailPresentation.is_default
                .is_(True),
            )
        ).scalars().all()

        for presentation in presentations:
            if (
                exclude_presentation_id is None
                or presentation.id
                != exclude_presentation_id
            ):
                presentation.is_default = False

        db.flush()

    @classmethod
    def create_presentation(
        cls,
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
        normalized_barcode = (
            cls._normalize_optional_text(
                barcode
            )
        )

        cls._assert_barcode_available(
            db,
            branch_id=branch_id,
            barcode=normalized_barcode,
        )

        if is_default:
            cls._unset_other_defaults(
                db,
                item_id=item.id,
            )

        return (
            RetailCatalogService
            .create_presentation(
                db,
                item=item,
                branch_id=branch_id,
                name=name,
                barcode=normalized_barcode,
                conversion_factor=(
                    conversion_factor
                ),
                sale_price=sale_price,
                bulk_price=bulk_price,
                bulk_min_quantity=(
                    bulk_min_quantity
                ),
                is_default=is_default,
                is_active=is_active,
            )
        )

    @classmethod
    def update_presentation(
        cls,
        db: Session,
        *,
        presentation: RetailPresentation,
        changes: dict[str, object],
    ) -> RetailPresentation:
        if "name" in changes:
            value = changes["name"]

            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Presentation name "
                        "is required"
                    ),
                )

            presentation.name = (
                cls._normalize_required_text(
                    value,
                    field="Presentation name",
                )
            )

        if "barcode" in changes:
            value = changes["barcode"]

            if (
                value is not None
                and not isinstance(value, str)
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid barcode",
                )

            normalized_barcode = (
                cls._normalize_optional_text(
                    value
                )
            )

            cls._assert_barcode_available(
                db,
                branch_id=presentation.branch_id,
                barcode=normalized_barcode,
                exclude_presentation_id=(
                    presentation.id
                ),
            )

            presentation.barcode = (
                normalized_barcode
            )

        factor = (
            changes[
                "conversion_factor"
            ]
            if "conversion_factor" in changes
            else presentation.conversion_factor
        )

        if factor is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Conversion factor "
                    "cannot be null"
                ),
            )

        normalized_factor = Decimal(
            str(factor)
        )

        if (
            not normalized_factor.is_finite()
            or normalized_factor
            <= Decimal("0")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Conversion factor "
                    "must be positive"
                ),
            )

        price = (
            changes["sale_price"]
            if "sale_price" in changes
            else presentation.sale_price
        )

        if price is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Sale price cannot be null"
                ),
            )

        normalized_price = cls._money(price)

        bulk_price = (
            changes["bulk_price"]
            if "bulk_price" in changes
            else presentation.bulk_price
        )

        bulk_min = (
            changes[
                "bulk_min_quantity"
            ]
            if "bulk_min_quantity" in changes
            else presentation.bulk_min_quantity
        )

        if (
            (bulk_price is None)
            != (bulk_min is None)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Bulk price and threshold "
                    "must be provided together"
                ),
            )

        normalized_bulk_price = (
            cls._money(bulk_price)
            if bulk_price is not None
            else None
        )

        normalized_bulk_min = None

        if bulk_min is not None:
            normalized_bulk_min = Decimal(
                str(bulk_min)
            )

            if (
                not normalized_bulk_min.is_finite()
                or normalized_bulk_min
                <= Decimal("0")
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Bulk minimum quantity "
                        "must be positive"
                    ),
                )

        presentation.conversion_factor = (
            normalized_factor
        )
        presentation.sale_price = (
            normalized_price
        )
        presentation.bulk_price = (
            normalized_bulk_price
        )
        presentation.bulk_min_quantity = (
            normalized_bulk_min
        )

        if "is_default" in changes:
            value = changes["is_default"]

            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Default flag cannot "
                        "be null"
                    ),
                )

            if bool(value):
                cls._unset_other_defaults(
                    db,
                    item_id=presentation.item_id,
                    exclude_presentation_id=(
                        presentation.id
                    ),
                )

            presentation.is_default = bool(
                value
            )

        if "is_active" in changes:
            value = changes["is_active"]

            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Active flag cannot "
                        "be null"
                    ),
                )

            presentation.is_active = bool(
                value
            )

        db.flush()

        return presentation
