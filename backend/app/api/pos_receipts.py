from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_receipts import (
    EffectiveReceiptSettings,
    ReceiptSnapshotV1,
)
from app.services.pos_receipt_settings_service import PosReceiptSettingsService
from app.services.pos_receipt_service import PosReceiptService


router = APIRouter(
    prefix="/pos/receipts",
    tags=["POS Receipts"],
)


@router.get(
    "/settings",
    response_model=EffectiveReceiptSettings,
)
def get_receipt_settings(
    branch_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EffectiveReceiptSettings:
    return PosReceiptSettingsService.get_effective(
        db,
        branch_code,
    )



@router.get(
    "/{order_uuid}",
    response_model=ReceiptSnapshotV1,
)
def get_receipt(
    order_uuid: str,
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    db: Session = Depends(get_db),
) -> ReceiptSnapshotV1:
    row = PosReceiptService.get_for_order(
        db=db,
        order_uuid=order_uuid,
        branch_code=branch_code,
    )

    return row.snapshot_json
