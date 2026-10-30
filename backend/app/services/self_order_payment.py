import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pos_orders import (
    PosOrder,
    PosOrderItem,
    PosOrderItemModifier,
    PosOrderStation,
    PosPayment,
)
from app.models.self_orders import (
    SelfOrder,
    SelfOrderPaymentAttempt,
)
from app.services.pos_pricing_service import money
from app.services.self_order_service import (
    SelfOrderService,
)


PAYMENT_OUTCOMES = {
    'APPROVED',
    'DECLINED',
    'UNKNOWN',
}

NEW_ATTEMPT_STATUSES = {
    'AWAITING_PAYMENT',
    'PAYMENT_DECLINED',
}


@dataclass(frozen=True)
class PaymentResult:
    status: str
    external_reference: str | None = None


class SimulatedPaymentProvider:
    provider_name = 'SIMULATED'

    def __init__(
        self,
        *,
        outcome: str = 'APPROVED',
    ):
        normalized = outcome.strip().upper()

        if normalized not in PAYMENT_OUTCOMES:
            raise ValueError(
                'Unsupported simulated payment outcome'
            )

        self.outcome = normalized

    def charge(
        self,
        *,
        payment_attempt_uuid,
        amount,
    ) -> PaymentResult:
        return PaymentResult(
            status=self.outcome,
            external_reference=(
                f'sim-{payment_attempt_uuid}'
            ),
        )


class SelfOrderPaymentService:
    @staticmethod
    def _provider_name(provider) -> str:
        value = getattr(
            provider,
            'provider_name',
            provider.__class__.__name__,
        )

        return str(value)[:40]

    @staticmethod
    def _assert_provider_allowed(
        provider,
    ) -> None:
        if not isinstance(
            provider,
            SimulatedPaymentProvider,
        ):
            return

        app_env = str(
            getattr(
                settings,
                'APP_ENV',
                'production',
            )
        ).strip().lower()

        if app_env not in {
            'development',
            'qa',
        }:
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    'Simulated payments are only '
                    'available in development or QA'
                ),
            )

    @staticmethod
    def _locked_order(
        db: Session,
        order_id: int,
    ) -> SelfOrder:
        return (
            db.execute(
                select(SelfOrder)
                .where(
                    SelfOrder.id == order_id
                )
                .with_for_update()
            )
            .scalar_one()
        )

    @staticmethod
    def _locked_attempt(
        db: Session,
        attempt_id: int,
    ) -> SelfOrderPaymentAttempt:
        return (
            db.execute(
                select(
                    SelfOrderPaymentAttempt
                )
                .where(
                    SelfOrderPaymentAttempt.id
                    == attempt_id
                )
                .with_for_update()
            )
            .scalar_one()
        )

    @staticmethod
    def _existing_attempt(
        db: Session,
        payment_attempt_uuid: str,
    ):
        return (
            db.execute(
                select(
                    SelfOrderPaymentAttempt
                ).where(
                    SelfOrderPaymentAttempt
                    .payment_attempt_uuid
                    == payment_attempt_uuid
                )
            )
            .scalar_one_or_none()
        )

    @staticmethod
    def _refresh_order(
        db: Session,
        order_id: int,
    ) -> SelfOrder:
        order = db.get(
            SelfOrder,
            order_id,
        )

        db.refresh(order)

        return order

    @classmethod
    def _materialize_pos_order(
        cls,
        *,
        db: Session,
        self_order: SelfOrder,
        attempt: SelfOrderPaymentAttempt,
    ) -> PosOrder:
        existing = (
            db.execute(
                select(PosOrder).where(
                    PosOrder.self_order_id
                    == self_order.id
                )
            )
            .scalar_one_or_none()
        )

        if existing is not None:
            return existing

        created_at = datetime.now(
            timezone.utc
        )

        pos_order = PosOrder(
            order_uuid=str(uuid.uuid4()),
            branch_id=self_order.branch_id,
            customer_id=None,
            terminal_id=(
                self_order.device.device_code
            ),
            source=self_order.device.source,
            self_order_id=self_order.id,
            status='NEW',
            payment_status='PAID',
            subtotal=money(
                self_order.subtotal
            ),
            total=money(
                self_order.total
            ),
            currency=self_order.currency,
            notes=None,
            created_at_client=created_at,
        )

        db.add(pos_order)
        db.flush()

        prefix = (
            self_order.branch.code
            .replace('-', '')
            .upper()[:3]
        )

        pos_order.folio = (
            f'{prefix}-{pos_order.id:06d}'
        )

        required_stations = set()

        for snapshot_item in self_order.items:
            pos_item = PosOrderItem(
                order_id=pos_order.id,
                product_id=(
                    snapshot_item.product_id
                ),
                product_name=(
                    snapshot_item.product_name
                ),
                preparation_station=(
                    snapshot_item
                    .preparation_station
                ),
                quantity=(
                    snapshot_item.quantity
                ),
                unit_base_price=money(
                    snapshot_item
                    .unit_base_price
                ),
                unit_modifier_total=money(
                    snapshot_item
                    .unit_modifier_total
                ),
                unit_price=money(
                    snapshot_item.unit_price
                ),
                line_total=money(
                    snapshot_item.line_total
                ),
                notes=snapshot_item.notes,
            )

            db.add(pos_item)
            db.flush()

            for snapshot_modifier in (
                snapshot_item.modifiers
            ):
                db.add(
                    PosOrderItemModifier(
                        order_item_id=(
                            pos_item.id
                        ),
                        modifier_group_id=None,
                        modifier_option_id=(
                            snapshot_modifier
                            .modifier_option_id
                        ),
                        group_name=(
                            snapshot_modifier
                            .group_name
                        ),
                        option_name=(
                            snapshot_modifier
                            .option_name
                        ),
                        price_delta=money(
                            snapshot_modifier
                            .price_delta
                        ),
                    )
                )

            if (
                snapshot_item
                .preparation_station
                in {
                    'KITCHEN',
                    'BAR',
                }
            ):
                required_stations.add(
                    snapshot_item
                    .preparation_station
                )

        for station_name in sorted(
            required_stations
        ):
            db.add(
                PosOrderStation(
                    order=pos_order,
                    station=station_name,
                    status='NEW',
                )
            )

        if not required_stations:
            pos_order.status = 'READY'

        external_reference = (
            attempt.external_reference
        )

        if external_reference is not None:
            external_reference = (
                external_reference[:120]
            )

        db.add(
            PosPayment(
                payment_uuid=(
                    attempt
                    .payment_attempt_uuid
                ),
                order_id=pos_order.id,
                method='CARD_EXTERNAL',
                amount=money(
                    self_order.total
                ),
                amount_tendered=None,
                change_due=None,
                external_reference=(
                    external_reference
                ),
                created_at_client=(
                    created_at
                ),
            )
        )

        db.flush()

        return pos_order

    @classmethod
    def _mark_unknown(
        cls,
        *,
        db: Session,
        order_id: int,
        attempt_id: int,
    ) -> SelfOrder:
        order = cls._locked_order(
            db,
            order_id,
        )

        attempt = cls._locked_attempt(
            db,
            attempt_id,
        )

        if attempt.status == 'PROCESSING':
            attempt.status = 'UNKNOWN'
            order.status = 'PAYMENT_UNKNOWN'

            db.commit()

        return cls._refresh_order(
            db,
            order_id,
        )

    @classmethod
    def process(
        cls,
        *,
        db: Session,
        self_order_uuid,
        device_code: str,
        payment_attempt_uuid,
        provider,
    ) -> SelfOrder:
        cls._assert_provider_allowed(
            provider
        )

        order = SelfOrderService.get(
            db=db,
            self_order_uuid=str(
                self_order_uuid
            ),
            device_code=device_code,
        )

        order = cls._locked_order(
            db,
            order.id,
        )

        attempt_uuid = str(
            payment_attempt_uuid
        )

        existing_attempt = (
            cls._existing_attempt(
                db,
                attempt_uuid,
            )
        )

        if existing_attempt is not None:
            if (
                existing_attempt
                .self_order_id
                != order.id
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        'Payment attempt UUID is '
                        'already bound to another '
                        'self-order'
                    ),
                )

            return order

        if order.status == 'PAYMENT_UNKNOWN':
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    'Payment status is unknown; '
                    'do not attempt payment again'
                ),
            )

        if (
            order.status
            not in NEW_ATTEMPT_STATUSES
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    'Self-order cannot start '
                    'another payment attempt'
                ),
            )

        amount = money(
            order.total
        )

        attempt = SelfOrderPaymentAttempt(
            payment_attempt_uuid=(
                attempt_uuid
            ),
            self_order_id=order.id,
            provider=cls._provider_name(
                provider
            ),
            status='PROCESSING',
            amount=amount,
            external_reference=None,
        )

        db.add(attempt)

        order.status = (
            'PAYMENT_PROCESSING'
        )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()

            existing_attempt = (
                cls._existing_attempt(
                    db,
                    attempt_uuid,
                )
            )

            if existing_attempt is None:
                raise

            if (
                existing_attempt
                .self_order_id
                != order.id
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        'Payment attempt UUID is '
                        'already bound to another '
                        'self-order'
                    ),
                )

            return cls._refresh_order(
                db,
                order.id,
            )

        db.refresh(attempt)
        db.refresh(order)

        try:
            payment_result = (
                provider.charge(
                    payment_attempt_uuid=(
                        attempt_uuid
                    ),
                    amount=amount,
                )
            )
        except Exception:
            return cls._mark_unknown(
                db=db,
                order_id=order.id,
                attempt_id=attempt.id,
            )

        result_status = str(
            payment_result.status
        ).strip().upper()

        order = cls._locked_order(
            db,
            order.id,
        )

        attempt = cls._locked_attempt(
            db,
            attempt.id,
        )

        if attempt.status != 'PROCESSING':
            return order

        attempt.external_reference = (
            payment_result
            .external_reference
        )

        if result_status == 'DECLINED':
            attempt.status = 'DECLINED'
            order.status = (
                'PAYMENT_DECLINED'
            )

            db.commit()

            return cls._refresh_order(
                db,
                order.id,
            )

        if result_status != 'APPROVED':
            attempt.status = 'UNKNOWN'
            order.status = (
                'PAYMENT_UNKNOWN'
            )

            db.commit()

            return cls._refresh_order(
                db,
                order.id,
            )

        attempt.status = 'APPROVED'
        order.status = 'PAID'

        db.flush()

        cls._materialize_pos_order(
            db=db,
            self_order=order,
            attempt=attempt,
        )

        order.status = 'SUBMITTED'

        try:
            db.commit()
        except IntegrityError:
            db.rollback()

            recovered_order = (
                cls._refresh_order(
                    db,
                    order.id,
                )
            )

            existing_pos_order = (
                db.execute(
                    select(PosOrder).where(
                        PosOrder.self_order_id
                        == recovered_order.id
                    )
                )
                .scalar_one_or_none()
            )

            if existing_pos_order is None:
                raise

            recovered_attempt = (
                cls._existing_attempt(
                    db,
                    attempt_uuid,
                )
            )

            if recovered_attempt is not None:
                recovered_attempt.status = (
                    'APPROVED'
                )

            recovered_order.status = (
                'SUBMITTED'
            )

            db.commit()

            return cls._refresh_order(
                db,
                recovered_order.id,
            )

        return cls._refresh_order(
            db,
            order.id,
        )
