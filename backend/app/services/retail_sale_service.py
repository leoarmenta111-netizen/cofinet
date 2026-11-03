from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.pos_staff import PosStaff
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_sales import (
    RetailSale,
    RetailSaleLine,
)
from app.schemas.retail_sales import (
    RetailHeldSaleLineInput,
    RetailHeldSaleUpsert,
)
from app.services.retail_pricing_service import (
    RetailPricingService,
)


ZERO_MONEY = Decimal("0.00")
ONE_BASE_UNIT = Decimal("1.000")


class RetailSaleService:
    @staticmethod
    def _require_papeleria_staff(
        staff: PosStaff,
    ) -> None:
        module_code = getattr(
            staff,
            "module_code",
            None,
        )

        if module_code != "PAPELERIA":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Papeleria staff session required"
                ),
            )

        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive POS staff",
            )

    @staticmethod
    def _normalize_label(
        label: str | None,
    ) -> str | None:
        if label is None:
            return None

        normalized = label.strip()

        if not normalized:
            return None

        if len(normalized) > 160:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Held sale label is too long"
                ),
            )

        return normalized

    @staticmethod
    def _normalize_quantity(
        quantity: Decimal,
    ) -> Decimal:
        value = Decimal(
            str(quantity)
        )

        if (
            not value.is_finite()
            or value <= Decimal("0")
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Held sale quantity must "
                    "be positive"
                ),
            )

        return value

    @classmethod
    def _build_line(
        cls,
        db: Session,
        *,
        sale: RetailSale,
        payload: RetailHeldSaleLineInput,
        branch_id: int,
    ) -> RetailSaleLine:
        item = db.get(
            RetailCatalogItem,
            payload.item_id,
        )

        if (
            item is None
            or item.branch_id != branch_id
            or not item.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retail item not found",
            )

        quantity = cls._normalize_quantity(
            payload.quantity
        )

        presentation = None

        if item.item_type == "PRODUCT":
            if payload.presentation_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Product presentation "
                        "is required"
                    ),
                )

            presentation = db.get(
                RetailPresentation,
                payload.presentation_id,
            )

            if (
                presentation is None
                or presentation.item_id
                != item.id
                or presentation.branch_id
                != branch_id
                or not presentation.is_active
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_404_NOT_FOUND
                    ),
                    detail=(
                        "Retail presentation "
                        "not found"
                    ),
                )

            quote = RetailPricingService.quote(
                db,
                item=item,
                quantity=quantity,
                presentation_id=presentation.id,
            )

            presentation_id = (
                presentation.id
            )
            presentation_name = (
                presentation.name
            )
            barcode = presentation.barcode
            conversion_factor = Decimal(
                presentation.conversion_factor
            )

        elif item.item_type == "SERVICE":
            if payload.presentation_id is not None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Services do not use "
                        "presentations"
                    ),
                )

            quote = RetailPricingService.quote(
                db,
                item=item,
                quantity=quantity,
                presentation_id=None,
            )

            presentation_id = None
            presentation_name = None
            barcode = None
            conversion_factor = (
                ONE_BASE_UNIT
            )

        else:
            raise HTTPException(
                status_code=422,
                detail="Invalid retail item type",
            )

        return RetailSaleLine(
            sale_id=sale.id,
            item_id=item.id,
            item_type=item.item_type,
            sku=item.sku,
            item_name=item.name,
            presentation_id=presentation_id,
            presentation_name=(
                presentation_name
            ),
            barcode=barcode,
            conversion_factor=(
                conversion_factor
            ),
            quantity=quantity,
            unit_price=quote.unit_price,
            line_subtotal=quote.line_total,
            discount_amount=ZERO_MONEY,
            line_total=quote.line_total,
            unit_cost_snapshot=Decimal(
                item.cost
            ),
        )

    @classmethod
    def _replace_held_lines(
        cls,
        db: Session,
        *,
        sale: RetailSale,
        payload: RetailHeldSaleUpsert,
    ) -> None:
        if not payload.lines:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Held sale requires at least "
                    "one line"
                ),
            )

        sale.lines.clear()
        db.flush()

        subtotal = ZERO_MONEY

        for line_payload in payload.lines:
            line = cls._build_line(
                db,
                sale=sale,
                payload=line_payload,
                branch_id=sale.branch_id,
            )

            sale.lines.append(line)

            subtotal += Decimal(
                line.line_total
            )

        sale.subtotal = subtotal
        sale.discount_total = ZERO_MONEY
        sale.total = subtotal

        db.flush()

    @classmethod
    def hold(
        cls,
        db: Session,
        *,
        payload: RetailHeldSaleUpsert,
        staff: PosStaff,
        terminal_id: str,
    ) -> RetailSale:
        cls._require_papeleria_staff(
            staff
        )

        normalized_terminal = (
            terminal_id.strip()
        )

        if not normalized_terminal:
            raise HTTPException(
                status_code=422,
                detail="Terminal ID is required",
            )

        sale = RetailSale(
            sale_uuid=str(uuid4()),
            branch_id=staff.branch_id,
            module_code="PAPELERIA",
            terminal_id=normalized_terminal,
            cashier_staff_id=staff.id,
            status="HELD",
            label=cls._normalize_label(
                payload.label
            ),
            subtotal=ZERO_MONEY,
            discount_total=ZERO_MONEY,
            total=ZERO_MONEY,
            currency="MXN",
            receipt_snapshot=None,
        )

        db.add(sale)
        db.flush()

        cls._replace_held_lines(
            db,
            sale=sale,
            payload=payload,
        )

        return sale

    @classmethod
    def update_held(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        payload: RetailHeldSaleUpsert,
        staff: PosStaff,
        terminal_id: str,
    ) -> RetailSale:
        cls._require_papeleria_staff(
            staff
        )

        sale = db.execute(
            select(RetailSale)
            .options(
                selectinload(
                    RetailSale.lines
                )
            )
            .where(
                RetailSale.sale_uuid
                == sale_uuid,
                RetailSale.branch_id
                == staff.branch_id,
                RetailSale.module_code
                == "PAPELERIA",
            )
        ).scalar_one_or_none()

        if sale is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Held sale not found",
            )

        if sale.status != "HELD":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Only held sales can "
                    "be updated"
                ),
            )

        normalized_terminal = (
            terminal_id.strip()
        )

        if not normalized_terminal:
            raise HTTPException(
                status_code=422,
                detail="Terminal ID is required",
            )

        sale.terminal_id = (
            normalized_terminal
        )

        sale.cashier_staff_id = (
            staff.id
        )

        sale.label = (
            cls._normalize_label(
                payload.label
            )
        )

        cls._replace_held_lines(
            db,
            sale=sale,
            payload=payload,
        )

        return sale

    @classmethod
    def get_sale(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        staff: PosStaff,
    ) -> RetailSale:
        cls._require_papeleria_staff(
            staff
        )

        sale = db.execute(
            select(RetailSale)
            .options(
                selectinload(
                    RetailSale.lines
                ),
                selectinload(
                    RetailSale.payments
                ),
                selectinload(
                    RetailSale.returns
                ),
            )
            .where(
                RetailSale.sale_uuid
                == sale_uuid,
                RetailSale.branch_id
                == staff.branch_id,
                RetailSale.module_code
                == "PAPELERIA",
            )
        ).scalar_one_or_none()

        if sale is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retail sale not found",
            )

        return sale

    @classmethod
    def resume(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        staff: PosStaff,
    ) -> RetailSale:
        cls._require_papeleria_staff(
            staff
        )

        sale = db.execute(
            select(RetailSale)
            .options(
                selectinload(
                    RetailSale.lines
                ),
                selectinload(
                    RetailSale.payments
                ),
            )
            .where(
                RetailSale.sale_uuid
                == sale_uuid,
                RetailSale.branch_id
                == staff.branch_id,
                RetailSale.module_code
                == "PAPELERIA",
            )
        ).scalar_one_or_none()

        if sale is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Held sale not found",
            )

        if sale.status != "HELD":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sale is not held",
            )

        return sale

    @classmethod
    def list_held(
        cls,
        db: Session,
        *,
        staff: PosStaff,
    ) -> list[RetailSale]:
        cls._require_papeleria_staff(
            staff
        )

        return list(
            db.execute(
                select(RetailSale)
                .options(
                    selectinload(
                        RetailSale.lines
                    ),
                    selectinload(
                        RetailSale.payments
                    ),
                )
                .where(
                    RetailSale.branch_id
                    == staff.branch_id,
                    RetailSale.module_code
                    == "PAPELERIA",
                    RetailSale.status
                    == "HELD",
                )
                .order_by(
                    RetailSale.created_at.desc(),
                    RetailSale.id.desc(),
                )
            )
            .scalars()
            .all()
        )
