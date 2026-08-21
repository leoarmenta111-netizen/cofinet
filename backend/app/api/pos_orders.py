from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_orders import (
    PosOrderCreate,
    PosOrderResponse,
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
