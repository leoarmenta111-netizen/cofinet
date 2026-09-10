from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.branch import Branch
from app.models.pos_orders import (
    PosOrder,
    PosOrderItem,
    PosPayment,
)
from app.schemas.admin_pos_sales import (
    AdminPosSaleDetailResponse,
    AdminPosSaleItem,
    AdminPosSaleListItem,
    AdminPosSaleModifier,
    AdminPosSalePayment,
    AdminPosSalesListResponse,
    AdminPosSalesSummary,
)


ZERO = Decimal("0.00")


class AdminPosSalesService:
    @staticmethod
    def _normalize_branch(
        branch_code: str | None,
    ) -> str | None:
        if branch_code is None:
            return None

        normalized = branch_code.strip().lower()

        if normalized == "principal":
            return "nuevo-vallarta"

        return normalized

    @classmethod
    def list_sales(
        cls,
        db: Session,
        *,
        branch_code: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        payment_method: str | None,
        offset: int,
        limit: int,
    ) -> AdminPosSalesListResponse:
        branch_code = cls._normalize_branch(
            branch_code
        )

        if (
            date_from is not None
            and date_to is not None
            and date_to <= date_from
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_to must be later than date_from",
            )

        filters = [
            PosOrder.status != "CANCELLED",
        ]

        if branch_code:
            filters.append(
                Branch.code == branch_code
            )

        if date_from:
            filters.append(
                PosOrder.created_at_client >= date_from
            )

        if date_to:
            filters.append(
                PosOrder.created_at_client < date_to
            )

        if payment_method:
            filters.append(
                PosPayment.method == payment_method
            )

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        summary_stmt = (
            select(
                func.count(PosOrder.id),
                func.coalesce(
                    func.sum(PosOrder.total),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                PosPayment.method == "CASH",
                                PosOrder.total,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                PosPayment.method
                                == "CARD_EXTERNAL",
                                PosOrder.total,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .join(
                Branch,
                PosOrder.branch_id == Branch.id,
            )
            .join(
                PosPayment,
                PosPayment.order_id == PosOrder.id,
            )
            .where(*filters)
        )

        (
            sales_count,
            gross_total,
            cash_total,
            card_total,
        ) = db.execute(summary_stmt).one()

        # -------------------------------------------------
        # Sales list
        # -------------------------------------------------

        stmt = (
            select(PosOrder)
            .join(
                Branch,
                PosOrder.branch_id == Branch.id,
            )
            .join(
                PosPayment,
                PosPayment.order_id == PosOrder.id,
            )
            .options(
                joinedload(PosOrder.branch),
                joinedload(PosOrder.payments),
            )
            .where(*filters)
            .order_by(
                PosOrder.created_at_client.desc(),
                PosOrder.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        orders = (
            db.execute(stmt)
            .unique()
            .scalars()
            .all()
        )

        sales = []

        for order in orders:
            payment = (
                order.payments[0]
                if order.payments
                else None
            )

            sales.append(
                AdminPosSaleListItem(
                    id=order.id,
                    order_uuid=order.order_uuid,
                    folio=order.folio,
                    branch_code=order.branch.code,
                    branch_name=order.branch.name,
                    terminal_id=order.terminal_id,
                    status=order.status,
                    payment_status=order.payment_status,
                    payment_method=(
                        payment.method
                        if payment
                        else None
                    ),
                    total=Decimal(order.total),
                    created_at=order.created_at,
                    created_at_client=(
                        order.created_at_client
                    ),
                )
            )

        return AdminPosSalesListResponse(
            summary=AdminPosSalesSummary(
                sales_count=int(sales_count or 0),
                gross_total=Decimal(
                    gross_total or ZERO
                ),
                cash_total=Decimal(
                    cash_total or ZERO
                ),
                card_total=Decimal(
                    card_total or ZERO
                ),
            ),
            sales=sales,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def get_sale(
        db: Session,
        order_uuid: str,
    ) -> AdminPosSaleDetailResponse:
        stmt = (
            select(PosOrder)
            .options(
                joinedload(PosOrder.branch),
                joinedload(PosOrder.payments),
                joinedload(PosOrder.items)
                .joinedload(PosOrderItem.modifiers),
            )
            .where(
                PosOrder.order_uuid == order_uuid
            )
        )

        order = (
            db.execute(stmt)
            .unique()
            .scalar_one_or_none()
        )

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="POS sale not found",
            )

        payment = (
            order.payments[0]
            if order.payments
            else None
        )

        return AdminPosSaleDetailResponse(
            id=order.id,
            order_uuid=order.order_uuid,
            folio=order.folio,
            branch_code=order.branch.code,
            branch_name=order.branch.name,
            terminal_id=order.terminal_id,
            status=order.status,
            payment_status=order.payment_status,
            subtotal=Decimal(order.subtotal),
            total=Decimal(order.total),
            currency=order.currency,
            notes=order.notes,
            created_at=order.created_at,
            created_at_client=order.created_at_client,

            items=[
                AdminPosSaleItem(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_base_price=Decimal(
                        item.unit_base_price
                    ),
                    unit_modifier_total=Decimal(
                        item.unit_modifier_total
                    ),
                    unit_price=Decimal(
                        item.unit_price
                    ),
                    line_total=Decimal(
                        item.line_total
                    ),
                    notes=item.notes,
                    modifiers=[
                        AdminPosSaleModifier(
                            group_name=m.group_name,
                            option_name=m.option_name,
                            price_delta=Decimal(
                                m.price_delta
                            ),
                        )
                        for m in item.modifiers
                    ],
                )
                for item in order.items
            ],

            payment=(
                AdminPosSalePayment(
                    method=payment.method,
                    amount=Decimal(
                        payment.amount
                    ),
                    amount_tendered=(
                        Decimal(
                            payment.amount_tendered
                        )
                        if payment.amount_tendered
                        is not None
                        else None
                    ),
                    change_due=(
                        Decimal(
                            payment.change_due
                        )
                        if payment.change_due
                        is not None
                        else None
                    ),
                    external_reference=(
                        payment.external_reference
                    ),
                )
                if payment
                else None
            ),
        )
