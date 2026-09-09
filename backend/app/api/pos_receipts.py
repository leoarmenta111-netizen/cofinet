from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_receipts import EffectiveReceiptSettings
from app.services.pos_receipt_settings_service import PosReceiptSettingsService


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
