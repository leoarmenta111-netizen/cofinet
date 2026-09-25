from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.self_orders import SelfOrder
from app.schemas.self_orders import (
    SelfOrderCancelRequest,
    SelfOrderCreate,
    SelfOrderItemResponse,
    SelfOrderModifierResponse,
    SelfOrderPaymentAttemptCreate,
    SelfOrderResponse,
)
from app.services.pos_pricing_service import money
from app.services.self_order_payment import (
    SelfOrderPaymentService,
    SimulatedPaymentProvider,
)
from app.services.self_order_service import (
    SelfOrderService,
)


router = APIRouter(
    prefix='/self-orders',
    tags=['Self Orders'],
)


def _response(
    order: SelfOrder,
) -> SelfOrderResponse:
    pos_order = order.pos_order

    return SelfOrderResponse(
        self_order_uuid=(
            order.self_order_uuid
        ),
        branch_code=order.branch.code,
        device_code=(
            order.device.device_code
        ),
        source=order.device.source,
        status=order.status,
        subtotal=money(order.subtotal),
        total=money(order.total),
        currency=order.currency,
        expires_at=order.expires_at,
        created_at=order.created_at,
        items=[
            SelfOrderItemResponse(
                product_id=item.product_id,
                product_name=(
                    item.product_name
                ),
                preparation_station=(
                    item.preparation_station
                ),
                quantity=item.quantity,
                unit_base_price=money(
                    item.unit_base_price
                ),
                unit_modifier_total=money(
                    item.unit_modifier_total
                ),
                unit_price=money(
                    item.unit_price
                ),
                line_total=money(
                    item.line_total
                ),
                notes=item.notes,
                modifiers=[
                    SelfOrderModifierResponse(
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
            for item in order.items
        ],
        folio=(
            pos_order.folio
            if pos_order is not None
            else None
        ),
        pos_order_uuid=(
            pos_order.order_uuid
            if pos_order is not None
            else None
        ),
    )


@router.post(
    '',
    response_model=SelfOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_self_order(
    payload: SelfOrderCreate,
    db: Session = Depends(get_db),
) -> SelfOrderResponse:
    order = SelfOrderService.create(
        db=db,
        payload=payload,
    )

    return _response(order)


@router.get(
    '/{self_order_uuid}',
    response_model=SelfOrderResponse,
)
def get_self_order(
    self_order_uuid: str,
    device_code: str = Query(
        min_length=1,
        max_length=80,
    ),
    db: Session = Depends(get_db),
) -> SelfOrderResponse:
    order = SelfOrderService.get(
        db=db,
        self_order_uuid=self_order_uuid,
        device_code=device_code,
    )

    return _response(order)


@router.post(
    '/{self_order_uuid}/cancel',
    response_model=SelfOrderResponse,
)
def cancel_self_order(
    self_order_uuid: str,
    payload: SelfOrderCancelRequest,
    db: Session = Depends(get_db),
) -> SelfOrderResponse:
    order = SelfOrderService.cancel(
        db=db,
        self_order_uuid=self_order_uuid,
        device_code=payload.device_code,
    )

    return _response(order)


@router.post(
    '/{self_order_uuid}/payment-attempts',
    response_model=SelfOrderResponse,
)
def create_payment_attempt(
    self_order_uuid: str,
    payload: SelfOrderPaymentAttemptCreate,
    db: Session = Depends(get_db),
) -> SelfOrderResponse:
    provider = SimulatedPaymentProvider(
        outcome=payload.simulated_outcome,
    )

    order = SelfOrderPaymentService.process(
        db=db,
        self_order_uuid=self_order_uuid,
        device_code=payload.device_code,
        payment_attempt_uuid=(
            payload.payment_attempt_uuid
        ),
        provider=provider,
    )

    return _response(order)
