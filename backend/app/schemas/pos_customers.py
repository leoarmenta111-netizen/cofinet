from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PosCustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    birthday: date | None = None


class PosCustomerSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_uuid: str
    name: str
    phone: str
    phone_normalized: str
    email: str | None = None
    birthday: date | None = None
    last_activity_at: datetime | None = None
    created_at: datetime | None = None

    loyalty_points: int = 0
    visits: int = 0
    total_spent: Decimal = Decimal("0.00")
    last_purchase_at: datetime | None = None
