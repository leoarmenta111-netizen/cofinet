from datetime import datetime
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.auth.admin_security import (
    require_super_admin,
)
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin_pos_sales import (
    AdminPosSaleDetailResponse,
    AdminPosSalesListResponse,
)
from app.services.admin_pos_sales_service import (
    AdminPosSalesService,
)


router = APIRouter(
    prefix="/admin/pos/sales",
    tags=["Admin POS Sales"],
)


@router.get(
    "",
    response_model=AdminPosSalesListResponse,
    responses={
        401: {
            "description":
                "Invalid or missing bearer token"
        },
        403: {
            "description":
                "Super administrator access required"
        },
    },
)
def list_pos_sales(
    branch_code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    payment_method: (
        Literal["CASH", "CARD_EXTERNAL"]
        | None
    ) = None,
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminPosSalesListResponse:
    return AdminPosSalesService.list_sales(
        db,
        branch_code=branch_code,
        date_from=date_from,
        date_to=date_to,
        payment_method=payment_method,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{order_uuid}",
    response_model=AdminPosSaleDetailResponse,
    responses={
        401: {
            "description":
                "Invalid or missing bearer token"
        },
        403: {
            "description":
                "Super administrator access required"
        },
        404: {
            "description":
                "POS sale not found"
        },
    },
)
def get_pos_sale(
    order_uuid: str,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminPosSaleDetailResponse:
    return AdminPosSalesService.get_sale(
        db,
        order_uuid,
    )
