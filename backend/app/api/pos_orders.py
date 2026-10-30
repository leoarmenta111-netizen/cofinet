from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_orders import (
    PosOrderCreate,
    PosOrderListResponse,
    PosOrderResponse,
    PosOrderStationStatusResponse,
    PosOrderStationStatusUpdate,
    PosOrderStatusUpdate,
    PosStationFeedResponse,
)
from app.services.pos_order_service import (
    PosOrderService,
)


router = APIRouter(
    prefix="/pos/orders",
    tags=["POS Orders"],
)


@router.post(
    "",
    response_model=PosOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pos_order(
    payload: PosOrderCreate,
    db: Session = Depends(get_db),
) -> PosOrderResponse:
    return PosOrderService.create(
        db=db,
        payload=payload,
    )


@router.post(
    "/sync",
    response_model=PosOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def sync_pos_order(
    payload: PosOrderCreate,
    db: Session = Depends(get_db),
) -> PosOrderResponse:
    return PosOrderService.sync_offline(
        db=db,
        payload=payload,
    )


@router.get(
    "",
    response_model=PosOrderListResponse,
)
def list_pos_orders(
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    order_status: Literal[
        "NEW",
        "PREPARING",
        "READY",
        "DELIVERED",
        "CANCELLED",
    ] | None = Query(
        default=None,
        alias="status",
    ),
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
    ),
    db: Session = Depends(get_db),
) -> PosOrderListResponse:
    return PosOrderService.list_orders(
        db=db,
        branch_code=branch_code,
        order_status=order_status,
        from_at=from_at,
        to_at=to_at,
        limit=limit,
    )


@router.get(
    "/stations/{station}",
    response_model=PosStationFeedResponse,
)
def list_station_orders(
    station: Literal[
        "KITCHEN",
        "BAR",
    ],
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    db: Session = Depends(get_db),
) -> PosStationFeedResponse:
    return PosOrderService.list_station_orders(
        db=db,
        branch_code=branch_code,
        station=station,
    )


@router.patch(
    "/{order_uuid}/stations/{station}",
    response_model=PosOrderStationStatusResponse,
)
def update_station_status(
    order_uuid: str,
    station: Literal[
        "KITCHEN",
        "BAR",
    ],
    payload: PosOrderStationStatusUpdate,
    db: Session = Depends(get_db),
) -> PosOrderStationStatusResponse:
    return PosOrderService.update_station_status(
        db=db,
        order_uuid=order_uuid,
        station=station,
        payload=payload,
    )


@router.get(
    "/{order_uuid}",
    response_model=PosOrderResponse,
)
def get_pos_order(
    order_uuid: str,
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    db: Session = Depends(get_db),
) -> PosOrderResponse:
    return PosOrderService.get_order(
        db=db,
        branch_code=branch_code,
        order_uuid=order_uuid,
    )


@router.patch(
    "/{order_uuid}/status",
    response_model=PosOrderResponse,
)
def update_pos_order_status(
    order_uuid: str,
    payload: PosOrderStatusUpdate,
    db: Session = Depends(get_db),
) -> PosOrderResponse:
    return PosOrderService.update_status(
        db=db,
        order_uuid=order_uuid,
        payload=payload,
    )
