from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.branch import Branch
from app.models.pos_staff import PosStaff
from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_sales import (
    RetailPayment,
    RetailSale,
    RetailSaleLine,
)
from app.schemas.retail_sales import (
    RetailCheckoutLineInput,
    RetailCheckoutRequest,
    RetailHeldSaleLineInput,
    RetailHeldSaleUpsert,
)
from app.services.pos_audit_service import PosAuditService
from app.services.pos_cash_service import (
    PosCashService,
)
from app.services.retail_inventory_service import (
    RetailInventoryService,
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

    @staticmethod
    def _checkout_money(
        value: Decimal,
        *,
        field: str,
    ) -> Decimal:
        try:
            normalized = Decimal(
                str(value)
            ).quantize(
                Decimal("0.01")
            )
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {field}",
            ) from exc

        if (
            not normalized.is_finite()
            or normalized < ZERO_MONEY
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {field}",
            )

        return normalized

    @classmethod
    def _validate_checkout_manager(
        cls,
        *,
        staff: PosStaff,
        manager: PosStaff | None,
        discount_required: bool,
    ) -> None:
        if not discount_required:
            return

        if manager is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "Manager authorization required"
                ),
            )

        manager_role = getattr(
            manager.role,
            "value",
            manager.role,
        )

        if (
            not manager.is_active
            or manager.branch_id
            != staff.branch_id
            or manager.module_code
            != "PAPELERIA"
            or manager_role != "MANAGER"
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "Manager authorization required"
                ),
            )

    @classmethod
    def _checkout_line(
        cls,
        db: Session,
        *,
        sale: RetailSale,
        payload: RetailCheckoutLineInput,
    ) -> tuple[
        RetailSaleLine,
        RetailCatalogItem,
        RetailPresentation | None,
    ]:
        item = db.get(
            RetailCatalogItem,
            payload.item_id,
        )

        if (
            item is None
            or item.branch_id
            != sale.branch_id
            or not item.is_active
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
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
                != sale.branch_id
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

        elif item.item_type == "SERVICE":
            if payload.presentation_id is not None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Services do not use "
                        "presentations"
                    ),
                )

        else:
            raise HTTPException(
                status_code=422,
                detail="Invalid retail item type",
            )

        quote = RetailPricingService.quote(
            db,
            item=item,
            quantity=quantity,
            presentation_id=(
                presentation.id
                if presentation is not None
                else None
            ),
        )

        line_subtotal = cls._checkout_money(
            quote.line_total,
            field="line subtotal",
        )

        line_discount = cls._checkout_money(
            payload.discount_amount,
            field="line discount",
        )

        if line_discount > line_subtotal:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Line discount exceeds "
                    "line subtotal"
                ),
            )

        line_total = (
            line_subtotal
            - line_discount
        ).quantize(
            Decimal("0.01")
        )

        line = RetailSaleLine(
            item_id=item.id,
            item_type=item.item_type,
            sku=item.sku,
            item_name=item.name,
            presentation_id=(
                presentation.id
                if presentation is not None
                else None
            ),
            presentation_name=(
                presentation.name
                if presentation is not None
                else None
            ),
            barcode=(
                presentation.barcode
                if presentation is not None
                else None
            ),
            conversion_factor=(
                Decimal(
                    presentation.conversion_factor
                )
                if presentation is not None
                else ONE_BASE_UNIT
            ),
            quantity=quantity,
            unit_price=quote.unit_price,
            line_subtotal=line_subtotal,
            discount_amount=line_discount,
            line_total=line_total,
            unit_cost_snapshot=Decimal(
                item.cost
            ),
        )

        sale.lines.append(line)

        return (
            line,
            item,
            presentation,
        )

    @staticmethod
    def _acquire_checkout_idempotency_locks(
        db: Session,
        *,
        sale_uuid: str,
        payment_uuid: str,
    ) -> None:
        bind = db.get_bind()

        # SQLite unit tests do not support PostgreSQL
        # advisory locks. PostgreSQL production/test
        # transactions serialize equal checkout keys.
        if bind.dialect.name != "postgresql":
            return

        lock_keys = (
            f"retail-checkout-sale:{sale_uuid}",
            f"retail-checkout-payment:{payment_uuid}",
        )

        for lock_key in lock_keys:
            db.execute(
                text(
                    "SELECT pg_advisory_xact_lock("
                    "hashtext(:lock_key)"
                    ")"
                ),
                {
                    "lock_key": lock_key,
                },
            )

    @classmethod
    def checkout(
        cls,
        db: Session,
        *,
        payload: RetailCheckoutRequest,
        staff: PosStaff,
        terminal_id: str,
        manager: PosStaff | None,
    ) -> RetailSale:
        cls._require_papeleria_staff(
            staff
        )

        terminal = terminal_id.strip()

        if not terminal:
            raise HTTPException(
                status_code=422,
                detail="Terminal ID is required",
            )

        sale_uuid = payload.sale_uuid.strip()
        payment_uuid = (
            payload.payment_uuid.strip()
        )

        held_sale_uuid = (
            payload.held_sale_uuid.strip()
            if payload.held_sale_uuid
            is not None
            else None
        )

        if not sale_uuid:
            raise HTTPException(
                status_code=422,
                detail="Sale UUID is required",
            )

        if not payment_uuid:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Payment UUID is required"
                ),
            )

        if held_sale_uuid == "":
            raise HTTPException(
                status_code=422,
                detail=(
                    "Held sale UUID cannot "
                    "be blank"
                ),
            )

        if (
            held_sale_uuid is not None
            and held_sale_uuid != sale_uuid
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Held sale UUID must match "
                    "sale UUID"
                ),
            )

        if not payload.lines:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Checkout requires at least "
                    "one line"
                ),
            )

        cls._acquire_checkout_idempotency_locks(
            db,
            sale_uuid=sale_uuid,
            payment_uuid=payment_uuid,
        )

        existing_sale = db.execute(
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
                == sale_uuid
            )
        ).scalar_one_or_none()

        held_sale: RetailSale | None = None

        if existing_sale is not None:
            if (
                existing_sale.branch_id
                != staff.branch_id
                or existing_sale.module_code
                != "PAPELERIA"
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Sale UUID already exists"
                    ),
                )

            if existing_sale.status == "PAID":
                return existing_sale

            if (
                existing_sale.status == "HELD"
                and held_sale_uuid
                == existing_sale.sale_uuid
            ):
                held_sale = existing_sale

            else:
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Sale UUID already exists"
                    ),
                )

        existing_payment = db.execute(
            select(RetailPayment).where(
                RetailPayment.payment_uuid
                == payment_uuid
            )
        ).scalar_one_or_none()

        if existing_payment is not None:
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Payment UUID already exists"
                ),
            )

        line_discount_total = ZERO_MONEY

        for line_payload in payload.lines:
            line_discount_total += (
                cls._checkout_money(
                    line_payload.discount_amount,
                    field="line discount",
                )
            )

        sale_discount = cls._checkout_money(
            payload.sale_discount_amount,
            field="sale discount",
        )

        discount_required = (
            line_discount_total
            > ZERO_MONEY
            or sale_discount
            > ZERO_MONEY
        )

        cls._validate_checkout_manager(
            staff=staff,
            manager=manager,
            discount_required=(
                discount_required
            ),
        )

        branch = db.get(
            Branch,
            staff.branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Branch not found",
            )

        shift = None

        if payload.payment_method == "CASH":
            shift = PosCashService.current_shift(
                db,
                branch_code=branch.code,
                terminal_id=terminal,
                module_code="PAPELERIA",
            )

            if shift is None:
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Open Papeleria cash "
                        "shift required"
                    ),
                )

        if held_sale is None:
            sale = RetailSale(
                sale_uuid=sale_uuid,
                branch_id=staff.branch_id,
                module_code="PAPELERIA",
                terminal_id=terminal,
                cashier_staff_id=staff.id,
                status="PAID",
                label=None,
                subtotal=ZERO_MONEY,
                discount_total=ZERO_MONEY,
                total=ZERO_MONEY,
                currency="MXN",
                receipt_snapshot=None,
                paid_at=datetime.now(
                    timezone.utc
                ),
            )

            db.add(sale)
            db.flush()

        else:
            sale = held_sale

            # Held preview lines/prices must never
            # become the final paid snapshot.
            sale.lines.clear()
            db.flush()

            sale.terminal_id = terminal
            sale.cashier_staff_id = staff.id
            sale.status = "PAID"
            sale.subtotal = ZERO_MONEY
            sale.discount_total = ZERO_MONEY
            sale.total = ZERO_MONEY
            sale.receipt_snapshot = None
            sale.paid_at = datetime.now(
                timezone.utc
            )

            db.flush()

        subtotal = ZERO_MONEY
        actual_line_discount = ZERO_MONEY

        inventory_work: list[
            tuple[
                RetailSaleLine,
                RetailCatalogItem,
                RetailPresentation | None,
            ]
        ] = []

        for line_payload in payload.lines:
            (
                line,
                item,
                presentation,
            ) = cls._checkout_line(
                db,
                sale=sale,
                payload=line_payload,
            )

            db.flush()

            subtotal += Decimal(
                line.line_subtotal
            )

            actual_line_discount += Decimal(
                line.discount_amount
            )

            inventory_work.append(
                (
                    line,
                    item,
                    presentation,
                )
            )

        subtotal = subtotal.quantize(
            Decimal("0.01")
        )

        actual_line_discount = (
            actual_line_discount.quantize(
                Decimal("0.01")
            )
        )

        after_line_discounts = (
            subtotal
            - actual_line_discount
        ).quantize(
            Decimal("0.01")
        )

        if sale_discount > after_line_discounts:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Sale discount exceeds "
                    "remaining subtotal"
                ),
            )

        discount_total = (
            actual_line_discount
            + sale_discount
        ).quantize(
            Decimal("0.01")
        )

        total = (
            subtotal
            - discount_total
        ).quantize(
            Decimal("0.01")
        )

        sale.subtotal = subtotal
        sale.discount_total = (
            discount_total
        )
        sale.total = total

        if discount_total > ZERO_MONEY:
            if manager is None:
                raise HTTPException(
                    status_code=(
                        status.HTTP_403_FORBIDDEN
                    ),
                    detail=(
                        "Manager authorization "
                        "required"
                    ),
                )

            PosAuditService.record(
                db,
                event_type=(
                    "RETAIL_DISCOUNT_AUTHORIZED"
                ),
                branch_id=staff.branch_id,
                terminal_id=terminal,
                actor_staff_id=staff.id,
                authorizer_staff_id=manager.id,
                target_type="retail_sale",
                target_id=sale_uuid,
                metadata={
                    "discount_total": (
                        f"{discount_total:.2f}"
                    ),
                    "line_discount_total": (
                        f"{actual_line_discount:.2f}"
                    ),
                    "sale_discount_amount": (
                        f"{sale_discount:.2f}"
                    ),
                },
            )

        for (
            line,
            item,
            presentation,
        ) in inventory_work:
            RetailInventoryService.decrement_for_sale(
                db,
                item=item,
                presentation=presentation,
                quantity=Decimal(
                    line.quantity
                ),
                sale_id=sale.id,
                sale_line_id=line.id,
                idempotency_key=(
                    f"retail-sale:"
                    f"{sale_uuid}:"
                    f"line:{line.id}"
                ),
            )

        if payload.payment_method == "CASH":
            if payload.amount_tendered is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Cash tendered amount "
                        "is required"
                    ),
                )

            tendered = (
                cls._checkout_money(
                    payload.amount_tendered,
                    field="amount tendered",
                )
            )

            if tendered < total:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Cash tendered is less "
                        "than sale total"
                    ),
                )

            change_due = (
                tendered - total
            ).quantize(
                Decimal("0.01")
            )

            payment = RetailPayment(
                payment_uuid=payment_uuid,
                method="CASH",
                amount=total,
                amount_tendered=tendered,
                change_due=change_due,
                external_reference=None,
            )

            sale.payments.append(
                payment
            )

            PosCashService.append_ledger_entry(
                db,
                shift_id=shift.id,
                entry_type="RETAIL_SALE",
                amount=total,
                idempotency_key=(
                    f"retail-sale:{sale_uuid}"
                ),
                reference_type=(
                    "retail_sale"
                ),
                reference_id=sale_uuid,
            )

        elif payload.payment_method == "CARD":
            payment = RetailPayment(
                payment_uuid=payment_uuid,
                method="CARD",
                amount=total,
                amount_tendered=None,
                change_due=ZERO_MONEY,
                external_reference=(
                    payload.external_reference
                ),
            )

            sale.payments.append(
                payment
            )

        else:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Unsupported payment method"
                ),
            )

        db.flush()

        return sale
