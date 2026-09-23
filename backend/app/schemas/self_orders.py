from uuid import UUID

from pydantic import BaseModel, Field


class SelfOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=99)
    modifier_option_ids: list[int] = Field(
        default_factory=list
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
    )


class SelfOrderCreate(BaseModel):
    self_order_uuid: UUID
    branch_code: str = Field(
        min_length=1,
        max_length=50,
    )
    device_code: str = Field(
        min_length=1,
        max_length=80,
    )
    items: list[SelfOrderItemCreate] = Field(
        min_length=1
    )
