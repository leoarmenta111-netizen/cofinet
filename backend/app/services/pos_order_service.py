import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_customers import (
    Customer,
    LoyaltyLedgerEntry,
)
from app.models.pos_catalog import (
    PosBranchProduct,
    PosModifierOption,
    PosProduct,
)
from app.models.pos_orders import (
    PosOrder,
    PosOrderItem,
    PosOrderItemModifier,
    PosOrderStation,
    PosPayment,
)
from app.schemas.pos_orders import (
    PosOrderCreate,
    PosOrderItemResponse,
    PosOrderListResponse,
    PosOrderStatusUpdate,
    PosOrderModifierResponse,
    PosOrderResponse,
    PosOrderStationResponse,
    PosOrderStationStatusResponse,
    PosOrderStationStatusUpdate,
    PosPaymentResponse,
    PosStationFeedResponse,
    PosStationOrderItemResponse,
    PosStationOrderResponse,
)


from app.services.pos_receipt_service import PosReceiptService

CENT = Decimal("0.01")
LOYALTY_MXN_PER_POINT = Decimal("10.00")


def loyalty_points_for_total(value) -> int:
    total = Decimal(str(value))

    if total <= 0:
        return 0

    return int(
        total // LOYALTY_MXN_PER_POINT
    )


def money(value) -> Decimal:
    return Decimal(value).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


class PosOrderService:
    @staticmethod
    def _response(
        order: PosOrder,
    ) -> PosOrderResponse:
        payment = order.payments[0]

        return PosOrderResponse(
            id=order.id,
            order_uuid=order.order_uuid,
            folio=order.folio,
            branch_code=order.branch.code,
            terminal_id=order.terminal_id,
            customer_uuid=(
                order.customer.customer_uuid
                if order.customer is not None
                else None
            ),
            status=order.status,
            payment_status=order.payment_status,
            subtotal=money(order.subtotal),
            total=money(order.total),
            currency=order.currency,
            created_at_client=order.created_at_client,
            items=[
                PosOrderItemResponse(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    preparation_station=(
                        item.preparation_station
                    ),
                    quantity=item.quantity,
                    unit_price=money(item.unit_price),
                    line_total=money(item.line_total),
                    modifiers=[
                        PosOrderModifierResponse(
                            group_name=modifier.group_name,
                            option_name=modifier.option_name,
                            price_delta=money(
                                modifier.price_delta
                            ),
                        )
                        for modifier in item.modifiers
                    ],
                )
                for item in order.items
            ],
            stations=[
                PosOrderStationResponse(
                    station=station_state.station,
                    status=station_state.status,
                    started_at=station_state.started_at,
                    ready_at=station_state.ready_at,
                )
                for station_state in sorted(
                    order.station_states,
                    key=lambda row: row.station,
                )
            ],
            payment=PosPaymentResponse(
                method=payment.method,
                amount=money(payment.amount),
                amount_tendered=(
                    money(payment.amount_tendered)
                    if payment.amount_tendered is not None
                    else None
                ),
                change_due=(
                    money(payment.change_due)
                    if payment.change_due is not None
                    else None
                ),
                external_reference=(
                    payment.external_reference
                ),
            ),
        )

    @staticmethod
    def _recalculate_preparation_status(
        order: PosOrder,
    ) -> None:
        # Terminal states are controlled at whole-order level.
        # Station progress must never reopen them.
        if order.status in {
            "DELIVERED",
            "CANCELLED",
        }:
            return

        station_states = list(
            order.station_states
        )

        # No Kitchen/Bar work is required.
        if not station_states:
            order.status = "READY"
            return

        statuses = {
            row.status
            for row in station_states
        }

        if statuses == {"NEW"}:
            order.status = "NEW"
            return

        if statuses == {"READY"}:
            order.status = "READY"
            return

        # Any partial/mixed progress is PREPARING:
        # NEW + READY, NEW + PREPARING,
        # PREPARING + READY, etc.
        order.status = "PREPARING"

    @staticmethod
    def _normalize_branch_code(
        branch_code: str,
    ) -> str:
        normalized = branch_code.strip().lower()

        if normalized == "principal":
            return "nuevo-vallarta"

        return normalized


    @classmethod
    def _branch(
        cls,
        db: Session,
        branch_code: str,
    ) -> Branch:
        normalized = cls._normalize_branch_code(
            branch_code
        )

        branch = db.execute(
            select(Branch).where(
                Branch.code == normalized,
                Branch.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        return branch


    @classmethod
    def list_station_orders(
        cls,
        db: Session,
        branch_code: str,
        station: str,
    ) -> PosStationFeedResponse:
        branch = cls._branch(
            db,
            branch_code,
        )

        station_states = (
            db.execute(
                select(PosOrderStation)
                .join(
                    PosOrder,
                    PosOrder.id
                    == PosOrderStation.order_id,
                )
                .where(
                    PosOrder.branch_id == branch.id,
                    PosOrderStation.station == station,
                )
                .order_by(
                    PosOrder.created_at_client.asc(),
                    PosOrder.id.asc(),
                )
            )
            .scalars()
            .all()
        )

        orders = []

        for station_state in station_states:
            order = station_state.order

            station_items = [
                item
                for item in order.items
                if item.preparation_station == station
            ]

            orders.append(
                PosStationOrderResponse(
                    order_uuid=order.order_uuid,
                    folio=order.folio,
                    branch_code=order.branch.code,
                    station_status=(
                        station_state.status
                    ),
                    created_at_client=(
                        order.created_at_client
                    ),
                    notes=order.notes,
                    items=[
                        PosStationOrderItemResponse(
                            product_id=item.product_id,
                            product_name=(
                                item.product_name
                            ),
                            preparation_station=(
                                item.preparation_station
                            ),
                            quantity=item.quantity,
                            notes=item.notes,
                            unit_price=money(
                                item.unit_price
                            ),
                            line_total=money(
                                item.line_total
                            ),
                            modifiers=[
                                PosOrderModifierResponse(
                                    group_name=(
                                        modifier.group_name
                                    ),
                                    option_name=(
                                        modifier.option_name
                                    ),
                                    price_delta=money(
                                        modifier.price_delta
                                    ),
                                )
                                for modifier
                                in item.modifiers
                            ],
                        )
                        for item in station_items
                    ],
                )
            )

        return PosStationFeedResponse(
            station=station,
            count=len(orders),
            orders=orders,
        )

    @classmethod
    def update_station_status(
        cls,
        db: Session,
        order_uuid: str,
        station: str,
        payload: PosOrderStationStatusUpdate,
    ) -> PosOrderStationStatusResponse:
        branch = cls._branch(
            db,
            payload.branch_code,
        )

        order = db.execute(
            select(PosOrder)
            .where(
                PosOrder.order_uuid == order_uuid,
                PosOrder.branch_id == branch.id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        station_state = next(
            (
                row
                for row in order.station_states
                if row.station == station
            ),
            None,
        )

        if station_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order station not found",
            )

        next_status = payload.status

        if station_state.status != next_status:
            allowed = {
                "NEW": {"PREPARING"},
                "PREPARING": {"READY"},
                "READY": set(),
            }

            if next_status not in allowed.get(
                station_state.status,
                set(),
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Invalid station transition: "
                        f"{station_state.status} "
                        f"-> {next_status}"
                    ),
                )

            now = datetime.now(timezone.utc)

            if next_status == "PREPARING":
                if station_state.started_at is None:
                    station_state.started_at = now

            if next_status == "READY":
                station_state.ready_at = now

            station_state.status = next_status

            cls._recalculate_preparation_status(
                order
            )

            db.commit()
            db.refresh(order)
            db.refresh(station_state)

        return PosOrderStationStatusResponse(
            order_uuid=order.order_uuid,
            station=station_state.station,
            status=station_state.status,
            order_status=order.status,
            started_at=station_state.started_at,
            ready_at=station_state.ready_at,
        )

    @classmethod
    def list_orders(
        cls,
        db: Session,
        branch_code: str,
        order_status: str | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        limit: int = 100,
    ) -> PosOrderListResponse:
        branch = cls._branch(
            db,
            branch_code,
        )

        statement = (
            select(PosOrder)
            .where(
                PosOrder.branch_id == branch.id
            )
            .order_by(
                PosOrder.created_at_client.desc(),
                PosOrder.id.desc(),
            )
            .limit(limit)
        )

        if order_status:
            statement = statement.where(
                PosOrder.status == order_status
            )

        if from_at is not None:
            statement = statement.where(
                PosOrder.created_at_client >= from_at
            )

        if to_at is not None:
            statement = statement.where(
                PosOrder.created_at_client < to_at
            )

        orders = (
            db.execute(statement)
            .scalars()
            .all()
        )

        return PosOrderListResponse(
            count=len(orders),
            orders=[
                cls._response(order)
                for order in orders
            ],
        )


    @classmethod
    def get_order(
        cls,
        db: Session,
        branch_code: str,
        order_uuid: str,
    ) -> PosOrderResponse:
        branch = cls._branch(
            db,
            branch_code,
        )

        order = db.execute(
            select(PosOrder).where(
                PosOrder.order_uuid == order_uuid,
                PosOrder.branch_id == branch.id,
            )
        ).scalar_one_or_none()

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        return cls._response(order)


    @classmethod
    def update_status(
        cls,
        db: Session,
        order_uuid: str,
        payload: PosOrderStatusUpdate,
    ) -> PosOrderResponse:
        branch = cls._branch(
            db,
            payload.branch_code,
        )

        order = db.execute(
            select(PosOrder)
            .where(
                PosOrder.order_uuid == order_uuid,
                PosOrder.branch_id == branch.id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        next_status = payload.status

        if order.status == next_status:
            return cls._response(order)

        allowed = {
            "NEW": {"PREPARING"},
            "PREPARING": {"READY"},
            "READY": {"DELIVERED"},
            "DELIVERED": set(),
            "CANCELLED": set(),
        }

        if next_status not in allowed.get(
            order.status,
            set(),
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Invalid order transition: "
                    f"{order.status} -> {next_status}"
                ),
            )

        order.status = next_status

        db.commit()
        db.refresh(order)

        return cls._response(order)


    @classmethod
    def create(
        cls,
        db: Session,
        payload: PosOrderCreate,
    ) -> PosOrderResponse:
        order_uuid = str(payload.order_uuid)

        existing = db.execute(
            select(PosOrder).where(
                PosOrder.order_uuid == order_uuid
            )
        ).scalar_one_or_none()

        if existing:
            return cls._response(existing)


        if payload.folio is not None:
            existing_folio = db.execute(
                select(PosOrder).where(
                    PosOrder.folio
                    == payload.folio
                )
            ).scalar_one_or_none()

            if existing_folio is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Receipt folio already exists"
                    ),
                )

        customer = None

        if payload.customer_uuid is not None:
            customer = db.execute(
                select(Customer).where(
                    Customer.customer_uuid
                    == str(payload.customer_uuid)
                )
            ).scalar_one_or_none()

            if customer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found",
                )

        branch_code = payload.branch_code.strip().lower()

        if branch_code == "principal":
            branch_code = "nuevo-vallarta"

        branch = db.execute(
            select(Branch).where(
                Branch.code == branch_code,
                Branch.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        calculated_items = []
        subtotal = Decimal("0.00")

        for item_index, requested_item in enumerate(
            payload.items
        ):
            branch_product = db.execute(
                select(PosBranchProduct)
                .join(PosBranchProduct.product)
                .where(
                    PosBranchProduct.branch_id == branch.id,
                    PosBranchProduct.product_id
                    == requested_item.product_id,
                    PosBranchProduct.is_available.is_(True),
                    PosProduct.is_active.is_(True),
                )
            ).scalar_one_or_none()

            if branch_product is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Product is not available "
                        f"in this branch: "
                        f"{requested_item.product_id}"
                    ),
                )

            product = branch_product.product

            snapshot_item = None

            if payload.receipt_snapshot is not None:
                if item_index >= len(
                    payload.receipt_snapshot.items
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Receipt snapshot item count "
                            "does not match order"
                        ),
                    )

                snapshot_item = (
                    payload.receipt_snapshot.items[
                        item_index
                    ]
                )

                if (
                    snapshot_item.product_id
                    != requested_item.product_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Receipt product does not "
                            "match order item"
                        ),
                    )

                if (
                    snapshot_item.quantity
                    != requested_item.quantity
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Receipt quantity does not "
                            "match order item"
                        ),
                    )

            if not product.category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product category is inactive",
                )

            base_price = money(
                branch_product.price
                if branch_product.price is not None
                else product.base_price
            )

            requested_option_ids = list(
                dict.fromkeys(
                    requested_item.modifier_option_ids
                )
            )

            selected_by_group = defaultdict(list)

            if requested_option_ids:
                options = (
                    db.execute(
                        select(PosModifierOption).where(
                            PosModifierOption.id.in_(
                                requested_option_ids
                            ),
                            PosModifierOption.is_active.is_(True),
                        )
                    )
                    .scalars()
                    .all()
                )

                if len(options) != len(
                    requested_option_ids
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "One or more modifier options "
                            "are invalid"
                        ),
                    )

                for option in options:
                    selected_by_group[
                        option.group_id
                    ].append(option)

            active_groups = {}

            for link in product.modifier_links:
                group = link.modifier_group

                if group.is_active:
                    active_groups[group.id] = group

            for group_id in selected_by_group:
                if group_id not in active_groups:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Modifier option does not "
                            "belong to this product"
                        ),
                    )

            for group in active_groups.values():
                selected = selected_by_group.get(
                    group.id,
                    [],
                )

                selected_count = len(selected)

                if selected_count < group.min_select:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Modifier group '{group.name}' "
                            f"requires at least "
                            f"{group.min_select} selection(s)"
                        ),
                    )

                if selected_count > group.max_select:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Modifier group '{group.name}' "
                            f"allows at most "
                            f"{group.max_select} selection(s)"
                        ),
                    )

            modifier_total = Decimal("0.00")
            modifier_snapshots = []

            frozen_modifiers_by_option_id = {}

            if snapshot_item is not None:
                for frozen_modifier in snapshot_item.modifiers:
                    if (
                        frozen_modifier.modifier_option_id
                        is None
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                "Frozen modifier must include "
                                "modifier_option_id"
                            ),
                        )

                    frozen_modifiers_by_option_id[
                        frozen_modifier.modifier_option_id
                    ] = frozen_modifier

                if set(
                    frozen_modifiers_by_option_id
                ) != set(requested_option_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Receipt modifiers do not "
                            "match order selections"
                        ),
                    )

            for group_id, options in selected_by_group.items():
                group = active_groups[group_id]

                for option in options:
                    if snapshot_item is not None:
                        frozen_modifier = (
                            frozen_modifiers_by_option_id[
                                option.id
                            ]
                        )

                        if (
                            frozen_modifier.modifier_group_id
                            is not None
                            and frozen_modifier.modifier_group_id
                            != group.id
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=(
                                    "Receipt modifier group "
                                    "does not match catalog"
                                ),
                            )

                        delta = money(
                            Decimal(
                                frozen_modifier.price_delta_cents
                            )
                            / Decimal("100")
                        )

                        group_name = (
                            frozen_modifier.group_name
                            or group.name
                        )

                        option_name = (
                            frozen_modifier.option_name
                        )
                    else:
                        delta = money(
                            option.price_delta
                        )
                        group_name = group.name
                        option_name = option.name

                    modifier_total += delta

                    modifier_snapshots.append(
                        {
                            "group_id": group.id,
                            "option_id": option.id,
                            "group_name": group_name,
                            "option_name": option_name,
                            "price_delta": delta,
                        }
                    )

            if snapshot_item is not None:
                snapshot_modifier_total_cents = sum(
                    modifier.price_delta_cents
                    for modifier
                    in snapshot_item.modifiers
                )

                modifier_total = money(
                    Decimal(
                        snapshot_modifier_total_cents
                    )
                    / Decimal("100")
                )

                unit_price = money(
                    Decimal(
                        snapshot_item.unit_price_cents
                    )
                    / Decimal("100")
                )

                line_total = money(
                    Decimal(
                        snapshot_item.line_total_cents
                    )
                    / Decimal("100")
                )

                base_price = money(
                    unit_price - modifier_total
                )
            else:
                unit_price = money(
                    base_price + modifier_total
                )

                line_total = money(
                    unit_price
                    * requested_item.quantity
                )

            if unit_price < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Calculated product price is invalid",
                )

            subtotal += line_total

            calculated_items.append(
                {
                    "product": product,
                    "quantity": requested_item.quantity,
                    "base_price": base_price,
                    "modifier_total": money(
                        modifier_total
                    ),
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "notes": requested_item.notes,
                    "modifiers": modifier_snapshots,
                }
            )

        subtotal = money(subtotal)

        if payload.receipt_snapshot is not None:
            total = money(
                Decimal(
                    payload.receipt_snapshot
                    .totals.total_cents
                )
                / Decimal("100")
            )
        else:
            total = subtotal

        payment_method = payload.payment.method

        if payload.receipt_snapshot is not None:
            snapshot = payload.receipt_snapshot

            if (
                snapshot.branch.branch_code
                != branch.code
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Receipt branch does not "
                        "match order branch"
                    ),
                )

            if (
                snapshot.terminal.terminal_id
                != payload.terminal_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Receipt terminal does not "
                        "match order terminal"
                    ),
                )

            if (
                snapshot.payment.method
                != payment_method
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Receipt payment method does not "
                        "match order payment method"
                    ),
                )

            if payment_method == "CASH":
                snapshot_tendered_cents = (
                    snapshot.payment.amount_tendered_cents
                )

                if (
                    snapshot_tendered_cents is not None
                    and payload.payment.amount_tendered
                    is not None
                ):
                    payload_tendered_cents = int(
                        money(
                            payload.payment.amount_tendered
                        )
                        * 100
                    )

                    if (
                        snapshot_tendered_cents
                        != payload_tendered_cents
                    ):
                        raise HTTPException(
                            status_code=(
                                status.HTTP_400_BAD_REQUEST
                            ),
                            detail=(
                                "Receipt tendered amount does "
                                "not match order payment"
                            ),
                        )

        amount_tendered = None
        change_due = None

        if payment_method == "CASH":
            if payload.payment.amount_tendered is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cash payment requires "
                        "amount_tendered"
                    ),
                )

            amount_tendered = money(
                payload.payment.amount_tendered
            )

            if amount_tendered < total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient cash received",
                )

            change_due = money(
                amount_tendered - total
            )

        if customer is not None:
            customer.last_activity_at = (
                payload.created_at_client
            )

        order = PosOrder(
            order_uuid=order_uuid,
            branch_id=branch.id,
            customer_id=(
                customer.id
                if customer is not None
                else None
            ),
            terminal_id=payload.terminal_id,
            status="NEW",
            payment_status="PAID",
            subtotal=subtotal,
            total=total,
            currency="MXN",
            notes=payload.notes,
            created_at_client=payload.created_at_client,
        )

        db.add(order)
        db.flush()

        if payload.folio is not None:
            order.folio = payload.folio
        else:
            prefix = (
                branch.code
                .replace("-", "")
                .upper()[:3]
            )

            order.folio = (
                f"{prefix}-{order.id:06d}"
            )

        for calculated in calculated_items:
            item = PosOrderItem(
                order_id=order.id,
                product_id=calculated["product"].id,
                product_name=calculated["product"].name,
                preparation_station=(
                    calculated["product"].preparation_station
                ),
                quantity=calculated["quantity"],
                unit_base_price=calculated["base_price"],
                unit_modifier_total=calculated[
                    "modifier_total"
                ],
                unit_price=calculated["unit_price"],
                line_total=calculated["line_total"],
                notes=calculated["notes"],
            )

            db.add(item)
            db.flush()

            for modifier in calculated["modifiers"]:
                db.add(
                    PosOrderItemModifier(
                        order_item_id=item.id,
                        modifier_group_id=modifier[
                            "group_id"
                        ],
                        modifier_option_id=modifier[
                            "option_id"
                        ],
                        group_name=modifier[
                            "group_name"
                        ],
                        option_name=modifier[
                            "option_name"
                        ],
                        price_delta=modifier[
                            "price_delta"
                        ],
                    )
                )

        required_stations = {
            calculated[
                "product"
            ].preparation_station
            for calculated in calculated_items
            if calculated[
                "product"
            ].preparation_station
            in {
                "KITCHEN",
                "BAR",
            }
        }

        for station_name in sorted(
            required_stations
        ):
            db.add(
                PosOrderStation(
                    order=order,
                    station=station_name,
                    status="NEW",
                )
            )

        db.flush()

        cls._recalculate_preparation_status(
            order
        )

        payment = PosPayment(
            payment_uuid=str(
                payload.payment.payment_uuid
            ),
            order_id=order.id,
            method=payment_method,
            amount=total,
            amount_tendered=amount_tendered,
            change_due=change_due,
            external_reference=(
                payload.payment.external_reference
            ),
            created_at_client=(
                payload.payment.created_at_client
            ),
        )

        db.add(payment)

        if payload.receipt_snapshot is not None:
            PosReceiptService.create_for_order(
                db=db,
                order=order,
                snapshot=payload.receipt_snapshot,
            )

        loyalty_points = (
            loyalty_points_for_total(total)
            if customer is not None
            else 0
        )

        if loyalty_points > 0:
            db.add(
                LoyaltyLedgerEntry(
                    entry_uuid=str(uuid.uuid4()),
                    customer_id=customer.id,
                    points=loyalty_points,
                    entry_type="EARN",
                    order_uuid=order_uuid,
                    branch_id=branch.id,
                    idempotency_key=(
                        f"SALE_EARN:{order_uuid}"
                    ),
                )
            )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()

            existing = db.execute(
                select(PosOrder).where(
                    PosOrder.order_uuid == order_uuid
                )
            ).scalar_one_or_none()

            if existing:
                return cls._response(existing)

            raise

        db.refresh(order)

        return cls._response(order)
