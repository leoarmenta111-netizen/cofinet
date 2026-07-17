from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.purchase import PurchaseStatus


class PurchaseCreate(BaseModel):
    plan_id: int = Field(gt=0)


class PurchaseResponse(BaseModel):
    purchase_id: int
    plan: str
    pin: str
    duration_minutes: int
    expires_at: datetime
    status: PurchaseStatus


class PurchaseList(BaseModel):
    purchases: list[PurchaseResponse]


class GuestPurchaseResponse(BaseModel):
    purchase_id: int
    plan: str
    amount: Decimal
    status: PurchaseStatus


class GuestPurchaseStatusResponse(BaseModel):
    status: PurchaseStatus
    pin: str | None = None
    expires_at: datetime | None = None
