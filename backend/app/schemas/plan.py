from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class AdminPlanUpdate(BaseModel):
    """Editable commercial fields exposed by the administrator catalogue."""

    price: Decimal | None = Field(
        default=None, ge=0, allow_inf_nan=False, max_digits=10, decimal_places=2
    )
    duration_minutes: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_numeric_change(self) -> "AdminPlanUpdate":
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("At least one numeric plan field is required")
        return self


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool
    created_at: datetime
