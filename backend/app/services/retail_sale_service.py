from datetime import datetime, timezone
from decimal import Decimal

from typing import Any

from app.models.branch import Branch
from app.models.pos_audit import PosAuditEvent
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)
from app.models.retail_sales import (
    RetailReturn,
    RetailReturnLine,
)
from app.services.pos_audit_service import PosAuditService
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
from app.services.retail_receipt_service import RetailReceiptService
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


    @staticmethod
    def _retail_return_money(
        value: Any,
    ) -> Decimal:
        amount = Decimal(str(value)).quantize(
            Decimal("0.01")
        )

        if not amount.is_finite():
            raise HTTPException(
                status_code=422,
                detail="Invalid monetary amount",
            )

        return amount

    @staticmethod
    def _retail_return_quantity(
        value: Any,
    ) -> Decimal:
        quantity = Decimal(str(value)).quantize(
            Decimal("0.001")
        )

        if (
            not quantity.is_finite()
            or quantity <= Decimal("0.000")
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Return quantity must "
                    "be positive"
                ),
            )

        return quantity

    @classmethod
    def _require_return_manager(
        cls,
        *,
        staff: PosStaff,
        manager: PosStaff | None,
    ) -> None:
        cls._require_papeleria_staff(staff)

        if manager is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Manager authorization "
                    "is required"
                ),
            )

        cls._require_papeleria_staff(manager)

        if (
            manager.branch_id != staff.branch_id
            or manager.role != "MANAGER"
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Papeleria manager "
                    "authorization required"
                ),
            )

    @classmethod
    def _locked_retail_sale(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        staff: PosStaff,
    ) -> RetailSale:
        normalized_uuid = sale_uuid.strip()

        if not normalized_uuid:
            raise HTTPException(
                status_code=422,
                detail="Sale UUID is required",
            )

        sale = db.execute(
            select(RetailSale)
            .where(
                RetailSale.sale_uuid
                == normalized_uuid,
                RetailSale.branch_id
                == staff.branch_id,
                RetailSale.module_code
                == "PAPELERIA",
            )
            .with_for_update()
            .execution_options(
                populate_existing=True
            )
        ).scalar_one_or_none()

        if sale is None:
            raise HTTPException(
                status_code=404,
                detail="Retail sale not found",
            )

        return sale

    @staticmethod
    def _prior_return_lines(
        db: Session,
        *,
        sale_id: int,
    ) -> list[RetailReturnLine]:
        return list(
            db.execute(
                select(RetailReturnLine)
                .join(
                    RetailReturn,
                    RetailReturn.id
                    == RetailReturnLine.return_id,
                )
                .where(
                    RetailReturn.sale_id
                    == sale_id
                )
            )
            .scalars()
            .all()
        )

    @classmethod
    def _returned_quantity_by_line(
        cls,
        db: Session,
        *,
        sale_id: int,
    ) -> dict[int, Decimal]:
        totals: dict[int, Decimal] = {}

        for row in cls._prior_return_lines(
            db,
            sale_id=sale_id,
        ):
            line_id = int(row.sale_line_id)

            totals[line_id] = (
                totals.get(
                    line_id,
                    Decimal("0.000"),
                )
                + Decimal(row.quantity)
            ).quantize(
                Decimal("0.001")
            )

        return totals

    @classmethod
    def _returned_amount_by_line(
        cls,
        db: Session,
        *,
        sale_id: int,
    ) -> dict[int, Decimal]:
        totals: dict[int, Decimal] = {}

        for row in cls._prior_return_lines(
            db,
            sale_id=sale_id,
        ):
            line_id = int(row.sale_line_id)

            totals[line_id] = (
                totals.get(
                    line_id,
                    Decimal("0.00"),
                )
                + Decimal(row.line_total)
            ).quantize(
                Decimal("0.01")
            )

        return totals

    @classmethod
    def _sale_line_refund_caps(
        cls,
        sale: RetailSale,
    ) -> dict[int, Decimal]:
        ordered = sorted(
            list(sale.lines),
            key=lambda line: line.id,
        )

        if not ordered:
            return {}

        weights = {
            line.id: Decimal(
                line.line_total
            )
            for line in ordered
        }

        weight_total = sum(
            weights.values(),
            Decimal("0.00"),
        )

        sale_total = cls._retail_return_money(
            sale.total
        )

        if weight_total <= Decimal("0.00"):
            return {
                line.id: Decimal("0.00")
                for line in ordered
            }

        caps: dict[int, Decimal] = {}
        allocated = Decimal("0.00")

        for line in ordered[:-1]:
            cap = (
                sale_total
                * weights[line.id]
                / weight_total
            ).quantize(
                Decimal("0.01")
            )

            caps[line.id] = cap
            allocated += cap

        caps[ordered[-1].id] = (
            sale_total - allocated
        ).quantize(
            Decimal("0.01")
        )

        return caps

    @classmethod
    def _original_sale_movement(
        cls,
        db: Session,
        *,
        sale_line_id: int,
    ) -> RetailInventoryMovement | None:
        return db.execute(
            select(RetailInventoryMovement)
            .where(
                RetailInventoryMovement.sale_line_id
                == sale_line_id,
                RetailInventoryMovement.movement_type
                == "SALE",
            )
        ).scalar_one_or_none()

    @classmethod
    def _restore_stock_effect(
        cls,
        db: Session,
        *,
        sale: RetailSale,
        line: RetailSaleLine,
        quantity: Decimal,
        movement_type: str,
        idempotency_key: str,
        reason: str,
        staff: PosStaff,
        manager: PosStaff,
    ) -> None:
        original = cls._original_sale_movement(
            db,
            sale_line_id=line.id,
        )

        # SERVICE and non-tracked items have no SALE
        # inventory movement, therefore no reversal.
        if original is None:
            return

        sold_quantity = Decimal(
            line.quantity
        ).quantize(
            Decimal("0.001")
        )

        if sold_quantity <= Decimal("0.000"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Invalid original sale "
                    "quantity"
                ),
            )

        original_base_effect = abs(
            Decimal(original.quantity_delta)
        )

        base_quantity = (
            original_base_effect
            * quantity
            / sold_quantity
        ).quantize(
            Decimal("0.001")
        )

        balance = db.execute(
            select(RetailInventoryBalance)
            .where(
                RetailInventoryBalance.branch_id
                == original.branch_id,
                RetailInventoryBalance.item_id
                == original.item_id,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True
            )
        ).scalar_one_or_none()

        if balance is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Inventory balance is "
                    "not configured"
                ),
            )

        RetailInventoryService.apply_movement(
            db,
            balance=balance,
            movement_type=movement_type,
            quantity_delta=base_quantity,
            idempotency_key=idempotency_key,
            note=reason,
            actor_staff_id=staff.id,
            authorizer_staff_id=manager.id,
            sale_id=sale.id,
            sale_line_id=line.id,
        )

    @classmethod
    def _apply_retail_refund(
        cls,
        db: Session,
        *,
        sale: RetailSale,
        refund_method: str,
        amount: Decimal,
        idempotency_key: str,
        reference_type: str,
        reference_id: str,
        external_reference: str | None,
    ) -> None:
        method = refund_method.strip().upper()

        if method not in {"CASH", "CARD"}:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Refund method must be "
                    "CASH or CARD"
                ),
            )

        if method == "CARD":
            if (
                external_reference is None
                or not external_reference.strip()
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Card refund reference "
                        "is required"
                    ),
                )

            # V1 intentionally does not call a
            # payment processor.
            return

        branch = db.get(
            Branch,
            sale.branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=404,
                detail="Branch not found",
            )

        shift = PosCashService.current_shift(
            db,
            branch_code=branch.code,
            terminal_id=sale.terminal_id,
            module_code="PAPELERIA",
        )

        if shift is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Open Papeleria cash "
                    "shift required"
                ),
            )

        PosCashService.append_ledger_entry(
            db,
            shift_id=shift.id,
            entry_type="RETAIL_REFUND",
            amount=-amount,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    @classmethod
    def return_items(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        payload: Any,
        staff: PosStaff,
        manager: PosStaff | None,
    ) -> RetailReturn:
        cls._require_return_manager(
            staff=staff,
            manager=manager,
        )

        assert manager is not None

        sale = cls._locked_retail_sale(
            db,
            sale_uuid=sale_uuid,
            staff=staff,
        )

        return_uuid = str(
            payload.return_uuid
        ).strip()

        if not return_uuid:
            raise HTTPException(
                status_code=422,
                detail="Return UUID is required",
            )

        existing = db.execute(
            select(RetailReturn).where(
                RetailReturn.return_uuid
                == return_uuid
            )
        ).scalar_one_or_none()

        if existing is not None:
            if existing.sale_id != sale.id:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Return UUID already "
                        "used"
                    ),
                )

            return existing

        if sale.status not in {
            "PAID",
            "PARTIALLY_RETURNED",
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Sale cannot accept "
                    "returns"
                ),
            )

        reason = str(
            payload.reason
        ).strip()

        if not reason:
            raise HTTPException(
                status_code=422,
                detail="Return reason is required",
            )

        refund_method = str(
            payload.refund_method
        ).strip().upper()

        external_reference = getattr(
            payload,
            "external_reference",
            None,
        )

        payload_lines = list(
            payload.lines
        )

        if not payload_lines:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Return requires at "
                    "least one line"
                ),
            )

        requested_ids = [
            int(row.sale_line_id)
            for row in payload_lines
        ]

        if (
            len(requested_ids)
            != len(set(requested_ids))
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Duplicate return "
                    "sale line"
                ),
            )

        sale_lines = {
            line.id: line
            for line in sale.lines
        }

        returned_qty = (
            cls._returned_quantity_by_line(
                db,
                sale_id=sale.id,
            )
        )

        returned_amount = (
            cls._returned_amount_by_line(
                db,
                sale_id=sale.id,
            )
        )

        caps = cls._sale_line_refund_caps(
            sale
        )

        normalized: list[
            tuple[
                RetailSaleLine,
                Decimal,
                Decimal,
                Decimal,
            ]
        ] = []

        subtotal = Decimal("0.00")
        total = Decimal("0.00")

        current_quantities: dict[
            int,
            Decimal,
        ] = {}

        for row in payload_lines:
            line_id = int(
                row.sale_line_id
            )

            line = sale_lines.get(
                line_id
            )

            if line is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Retail sale line "
                        "not found"
                    ),
                )

            quantity = (
                cls._retail_return_quantity(
                    row.quantity
                )
            )

            sold_quantity = Decimal(
                line.quantity
            ).quantize(
                Decimal("0.001")
            )

            previous_quantity = (
                returned_qty.get(
                    line.id,
                    Decimal("0.000"),
                )
            )

            remaining_quantity = (
                sold_quantity
                - previous_quantity
            ).quantize(
                Decimal("0.001")
            )

            if quantity > remaining_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Return quantity exceeds "
                        "remaining sold quantity"
                    ),
                )

            cap = caps[line.id]

            prior_money = (
                returned_amount.get(
                    line.id,
                    Decimal("0.00"),
                )
            )

            remaining_money = (
                cap - prior_money
            ).quantize(
                Decimal("0.01")
            )

            if quantity == remaining_quantity:
                line_total = remaining_money
            else:
                line_total = (
                    cap
                    * quantity
                    / sold_quantity
                ).quantize(
                    Decimal("0.01")
                )

                if line_total > remaining_money:
                    line_total = remaining_money

            unit_amount = (
                line_total / quantity
            ).quantize(
                Decimal("0.01")
            )

            line_subtotal = (
                Decimal(line.line_subtotal)
                * quantity
                / sold_quantity
            ).quantize(
                Decimal("0.01")
            )

            subtotal += line_subtotal
            total += line_total

            current_quantities[
                line.id
            ] = quantity

            normalized.append(
                (
                    line,
                    quantity,
                    unit_amount,
                    line_total,
                )
            )

        subtotal = subtotal.quantize(
            Decimal("0.01")
        )

        total = total.quantize(
            Decimal("0.01")
        )

        if total <= Decimal("0.00"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Return has no refundable "
                    "amount"
                ),
            )

        retail_return = RetailReturn(
            return_uuid=return_uuid,
            sale_id=sale.id,
            cashier_staff_id=staff.id,
            authorizer_staff_id=manager.id,
            reason=reason,
            subtotal=subtotal,
            total=total,
        )

        db.add(retail_return)
        db.flush()

        for (
            line,
            quantity,
            unit_amount,
            line_total,
        ) in normalized:
            db.add(
                RetailReturnLine(
                    return_id=retail_return.id,
                    sale_line_id=line.id,
                    quantity=quantity,
                    unit_amount=unit_amount,
                    line_total=line_total,
                )
            )

            cls._restore_stock_effect(
                db,
                sale=sale,
                line=line,
                quantity=quantity,
                movement_type="RETURN",
                idempotency_key=(
                    f"retail-return:"
                    f"{return_uuid}:"
                    f"line:{line.id}"
                ),
                reason=reason,
                staff=staff,
                manager=manager,
            )

        cls._apply_retail_refund(
            db,
            sale=sale,
            refund_method=refund_method,
            amount=total,
            idempotency_key=(
                f"retail-return:"
                f"{return_uuid}"
            ),
            reference_type="retail_return",
            reference_id=return_uuid,
            external_reference=(
                external_reference
            ),
        )

        all_returned = True

        for line in sale.lines:
            cumulative = (
                returned_qty.get(
                    line.id,
                    Decimal("0.000"),
                )
                + current_quantities.get(
                    line.id,
                    Decimal("0.000"),
                )
            ).quantize(
                Decimal("0.001")
            )

            sold = Decimal(
                line.quantity
            ).quantize(
                Decimal("0.001")
            )

            if cumulative < sold:
                all_returned = False
                break

        sale.status = (
            "RETURNED"
            if all_returned
            else "PARTIALLY_RETURNED"
        )

        PosAuditService.record(
            db,
            event_type=(
                "RETAIL_RETURN_AUTHORIZED"
            ),
            branch_id=sale.branch_id,
            terminal_id=sale.terminal_id,
            actor_staff_id=staff.id,
            authorizer_staff_id=manager.id,
            target_type="retail_sale",
            target_id=sale.sale_uuid,
            metadata={
                "return_uuid": return_uuid,
                "reason": reason,
                "refund_method": (
                    refund_method
                ),
                "external_reference": (
                    external_reference
                ),
                "refund_amount": (
                    f"{total:.2f}"
                ),
                "quantities": [
                    {
                        "sale_line_id": (
                            line.id
                        ),
                        "quantity": (
                            f"{quantity:.3f}"
                        ),
                    }
                    for (
                        line,
                        quantity,
                        _unit_amount,
                        _line_total,
                    ) in normalized
                ],
            },
        )

        db.flush()

        return retail_return

    @classmethod
    def cancel_paid_sale(
        cls,
        db: Session,
        *,
        sale_uuid: str,
        payload: Any,
        staff: PosStaff,
        manager: PosStaff | None,
    ) -> RetailSale:
        cls._require_return_manager(
            staff=staff,
            manager=manager,
        )

        assert manager is not None

        sale = cls._locked_retail_sale(
            db,
            sale_uuid=sale_uuid,
            staff=staff,
        )

        cancellation_uuid = str(
            payload.cancellation_uuid
        ).strip()

        if not cancellation_uuid:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Cancellation UUID "
                    "is required"
                ),
            )

        prior_events = list(
            db.execute(
                select(PosAuditEvent).where(
                    PosAuditEvent.event_type
                    == (
                        "RETAIL_CANCELLATION_"
                        "AUTHORIZED"
                    ),
                    PosAuditEvent.target_type
                    == "retail_sale",
                    PosAuditEvent.target_id
                    == sale.sale_uuid,
                )
            )
            .scalars()
            .all()
        )

        for event in prior_events:
            metadata = (
                event.metadata_json
                or {}
            )

            if (
                metadata.get(
                    "cancellation_uuid"
                )
                == cancellation_uuid
            ):
                if sale.status == "CANCELLED":
                    return sale

        if sale.status == "CANCELLED":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Sale is already "
                    "cancelled"
                ),
            )

        if sale.status not in {
            "PAID",
            "PARTIALLY_RETURNED",
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Sale cannot be "
                    "cancelled"
                ),
            )

        reason = str(
            payload.reason
        ).strip()

        if not reason:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Cancellation reason "
                    "is required"
                ),
            )

        refund_method = str(
            payload.refund_method
        ).strip().upper()

        external_reference = getattr(
            payload,
            "external_reference",
            None,
        )

        returned_qty = (
            cls._returned_quantity_by_line(
                db,
                sale_id=sale.id,
            )
        )

        prior_returns = list(
            db.execute(
                select(RetailReturn).where(
                    RetailReturn.sale_id
                    == sale.id
                )
            )
            .scalars()
            .all()
        )

        already_refunded = sum(
            (
                Decimal(row.total)
                for row in prior_returns
            ),
            Decimal("0.00"),
        ).quantize(
            Decimal("0.01")
        )

        refund_amount = (
            Decimal(sale.total)
            - already_refunded
        ).quantize(
            Decimal("0.01")
        )

        if refund_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Sale has no remaining "
                    "refundable amount"
                ),
            )

        quantities: list[
            dict[str, object]
        ] = []

        for line in sale.lines:
            sold = Decimal(
                line.quantity
            ).quantize(
                Decimal("0.001")
            )

            returned = (
                returned_qty.get(
                    line.id,
                    Decimal("0.000"),
                )
            )

            remaining = (
                sold - returned
            ).quantize(
                Decimal("0.001")
            )

            if remaining <= Decimal("0.000"):
                continue

            cls._restore_stock_effect(
                db,
                sale=sale,
                line=line,
                quantity=remaining,
                movement_type=(
                    "CANCELLATION_REVERSAL"
                ),
                idempotency_key=(
                    f"retail-cancel:"
                    f"{cancellation_uuid}:"
                    f"line:{line.id}"
                ),
                reason=reason,
                staff=staff,
                manager=manager,
            )

            quantities.append(
                {
                    "sale_line_id": line.id,
                    "quantity": (
                        f"{remaining:.3f}"
                    ),
                }
            )

        cls._apply_retail_refund(
            db,
            sale=sale,
            refund_method=refund_method,
            amount=refund_amount,
            idempotency_key=(
                f"retail-cancel:"
                f"{cancellation_uuid}"
            ),
            reference_type=(
                "retail_cancellation"
            ),
            reference_id=(
                cancellation_uuid
            ),
            external_reference=(
                external_reference
            ),
        )

        sale.status = "CANCELLED"

        PosAuditService.record(
            db,
            event_type=(
                "RETAIL_CANCELLATION_"
                "AUTHORIZED"
            ),
            branch_id=sale.branch_id,
            terminal_id=sale.terminal_id,
            actor_staff_id=staff.id,
            authorizer_staff_id=manager.id,
            target_type="retail_sale",
            target_id=sale.sale_uuid,
            metadata={
                "cancellation_uuid": (
                    cancellation_uuid
                ),
                "reason": reason,
                "refund_method": (
                    refund_method
                ),
                "external_reference": (
                    external_reference
                ),
                "refund_amount": (
                    f"{refund_amount:.2f}"
                ),
                "quantities": quantities,
            },
        )

        db.flush()

        return sale

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

        if sale.receipt_snapshot is None:
            sale.receipt_snapshot = (
                RetailReceiptService
                .build_snapshot(
                    sale=sale,
                    branch=branch,
                    cashier=staff,
                    authorizer=manager,
                )
            )

        db.flush()

        return sale
