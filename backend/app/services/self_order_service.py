from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.self_orders import (
    SelfOrder,
    SelfOrderDevice,
    SelfOrderItem,
    SelfOrderItemModifier,
)
from app.schemas.self_orders import SelfOrderCreate
from app.services.pos_pricing_service import (
    PosPricingService,
    PricingItemRequest,
    money,
)


SELF_ORDER_TTL = timedelta(minutes=30)

EXPIRABLE_STATUSES = {
    'AWAITING_PAYMENT',
    'PAYMENT_DECLINED',
}

CANCELLABLE_STATUSES = {
    'AWAITING_PAYMENT',
    'PAYMENT_DECLINED',
}


class SelfOrderService:
    @staticmethod
    def _normalize_branch_code(
        branch_code: str,
    ) -> str:
        normalized = branch_code.strip().lower()

        if normalized == 'principal':
            return 'nuevo-vallarta'

        return normalized

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    @classmethod
    def _branch(
        cls,
        db: Session,
        branch_code: str,
    ) -> Branch:
        normalized = cls._normalize_branch_code(
            branch_code
        )

        branch = (
            db.execute(
                select(Branch).where(
                    Branch.code == normalized,
                    Branch.is_active.is_(True),
                )
            )
            .scalar_one_or_none()
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Branch not found',
            )

        return branch

    @staticmethod
    def _device(
        db: Session,
        device_code: str,
    ) -> SelfOrderDevice:
        normalized = device_code.strip()

        device = (
            db.execute(
                select(SelfOrderDevice).where(
                    SelfOrderDevice.device_code
                    == normalized,
                    SelfOrderDevice.is_active.is_(True),
                )
            )
            .scalar_one_or_none()
        )

        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Self-order device not found',
            )

        return device

    @classmethod
    def _assert_existing_identity(
        cls,
        order: SelfOrder,
        *,
        branch_code: str,
        device_code: str,
    ) -> None:
        expected_branch = (
            cls._normalize_branch_code(
                branch_code
            )
        )

        expected_device = (
            device_code.strip()
        )

        if (
            order.branch.code != expected_branch
            or order.device.device_code
            != expected_device
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    'Self-order UUID is already '
                    'bound to another device or branch'
                ),
            )

    @classmethod
    def _expire_if_needed(
        cls,
        db: Session,
        order: SelfOrder,
    ) -> SelfOrder:
        expires_at = cls._aware_utc(
            order.expires_at
        )

        now = datetime.now(timezone.utc)

        if (
            order.status in EXPIRABLE_STATUSES
            and expires_at <= now
        ):
            order.status = 'EXPIRED'
            db.commit()
            db.refresh(order)

        order.expires_at = cls._aware_utc(
            order.expires_at
        )

        return order

    @classmethod
    def create(
        cls,
        db: Session,
        payload: SelfOrderCreate,
    ) -> SelfOrder:
        order_uuid = str(
            payload.self_order_uuid
        )

        existing = (
            db.execute(
                select(SelfOrder).where(
                    SelfOrder.self_order_uuid
                    == order_uuid
                )
            )
            .scalar_one_or_none()
        )

        if existing is not None:
            cls._assert_existing_identity(
                existing,
                branch_code=payload.branch_code,
                device_code=payload.device_code,
            )

            return cls._expire_if_needed(
                db,
                existing,
            )

        branch = cls._branch(
            db,
            payload.branch_code,
        )

        device = cls._device(
            db,
            payload.device_code,
        )

        if device.branch_id != branch.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    'Self-order device does not '
                    'belong to requested branch'
                ),
            )

        priced_items = (
            PosPricingService.resolve_items(
                db=db,
                branch=branch,
                items=[
                    PricingItemRequest(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        modifier_option_ids=list(
                            item.modifier_option_ids
                        ),
                        notes=item.notes,
                    )
                    for item in payload.items
                ],
            )
        )

        subtotal = money(
            sum(
                (
                    item.line_total
                    for item in priced_items
                ),
                Decimal('0.00'),
            )
        )

        now = datetime.now(
            timezone.utc
        )

        expires_at = (
            now + SELF_ORDER_TTL
        )

        order = SelfOrder(
            self_order_uuid=order_uuid,
            branch_id=branch.id,
            device_id=device.id,
            status='AWAITING_PAYMENT',
            subtotal=subtotal,
            total=subtotal,
            currency='MXN',
            expires_at=expires_at,
        )

        db.add(order)
        db.flush()

        for priced in priced_items:
            item = SelfOrderItem(
                self_order_id=order.id,
                product_id=priced.product_id,
                product_name=priced.product_name,
                preparation_station=(
                    priced.preparation_station
                ),
                quantity=priced.quantity,
                unit_base_price=(
                    priced.unit_base_price
                ),
                unit_modifier_total=(
                    priced.unit_modifier_total
                ),
                unit_price=priced.unit_price,
                line_total=priced.line_total,
                notes=priced.notes,
            )

            db.add(item)
            db.flush()

            for modifier in priced.modifiers:
                db.add(
                    SelfOrderItemModifier(
                        self_order_item_id=item.id,
                        modifier_option_id=(
                            modifier.option_id
                        ),
                        group_name=(
                            modifier.group_name
                        ),
                        option_name=(
                            modifier.option_name
                        ),
                        price_delta=(
                            modifier.price_delta
                        ),
                    )
                )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()

            existing = (
                db.execute(
                    select(SelfOrder).where(
                        SelfOrder.self_order_uuid
                        == order_uuid
                    )
                )
                .scalar_one_or_none()
            )

            if existing is None:
                raise

            cls._assert_existing_identity(
                existing,
                branch_code=payload.branch_code,
                device_code=payload.device_code,
            )

            return cls._expire_if_needed(
                db,
                existing,
            )

        db.refresh(order)

        # SQLite does not preserve tzinfo on a
        # DateTime(timezone=True) round trip.
        order.expires_at = expires_at

        return order

    @classmethod
    def get(
        cls,
        db: Session,
        self_order_uuid: str,
        device_code: str,
    ) -> SelfOrder:
        order = (
            db.execute(
                select(SelfOrder).where(
                    SelfOrder.self_order_uuid
                    == str(self_order_uuid)
                )
            )
            .scalar_one_or_none()
        )

        if (
            order is None
            or order.device.device_code
            != device_code.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Self-order not found',
            )

        return cls._expire_if_needed(
            db,
            order,
        )

    @classmethod
    def cancel(
        cls,
        db: Session,
        self_order_uuid: str,
        device_code: str,
    ) -> SelfOrder:
        order = cls.get(
            db=db,
            self_order_uuid=self_order_uuid,
            device_code=device_code,
        )

        if order.status == 'CANCELLED':
            return order

        if order.status not in CANCELLABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    'Self-order can no longer '
                    'be cancelled'
                ),
            )

        order.status = 'CANCELLED'

        db.commit()
        db.refresh(order)

        order.expires_at = cls._aware_utc(
            order.expires_at
        )

        return order
