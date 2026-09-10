from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class AdminPosCustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    birthday: date | None = None


class AdminPosCustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    birthday: date | None = None


class AdminPosCustomerResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    customer_uuid: str
    name: str
    phone: str
    phone_normalized: str
    email: str | None = None
    birthday: date | None = None
    loyalty_points: int = 0
    visits: int = 0
    total_spent: Decimal = Decimal("0.00")
    last_purchase_at: datetime | None = None


class AdminPosLoyaltyAdjustmentCreate(BaseModel):
    points: int

    @field_validator("points")
    @classmethod
    def validate_points(
        cls,
        value: int,
    ) -> int:
        if value == 0:
            raise ValueError(
                "Loyalty adjustment cannot be zero"
            )

        return value


class AdminPosLoyaltyEntryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    entry_uuid: str
    points: int
    entry_type: str
    order_uuid: str | None = None
    created_at: datetime


class AdminPosCustomerProfileResponse(BaseModel):
    customer_uuid: str
    name: str
    phone: str
    phone_normalized: str
    email: str | None = None
    birthday: date | None = None

    created_at: datetime
    last_activity_at: datetime | None = None

    loyalty_points: int = 0
    visits: int = 0
    total_spent: Decimal = Decimal("0.00")
    last_purchase_at: datetime | None = None

    orders: list[dict] = []
    loyalty_history: list[AdminPosLoyaltyEntryResponse] = []
