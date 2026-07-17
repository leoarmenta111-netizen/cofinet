from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    duration_minutes: int = Field(gt=0)
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    duration_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool
    created_at: datetime
