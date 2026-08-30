from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PosOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=99)
    modifier_option_ids: list[int] = []
    notes: str | None = Field(default=None, max_length=500)


class PosPaymentCreate(BaseModel):
    payment_uuid: UUID
    method: Literal["CASH", "CARD_EXTERNAL"]
    amount_tendered: Decimal | None = Field(
        default=None,
        ge=0,
    )
    external_reference: str | None = Field(
        default=None,
        max_length=120,
    )
    created_at_client: datetime


class PosOrderCreate(BaseModel):
    order_uuid: UUID
    branch_code: str = Field(min_length=1, max_length=50)
    terminal_id: str = Field(min_length=1, max_length=80)
    customer_uuid: UUID | None = None
    created_at_client: datetime
    notes: str | None = Field(default=None, max_length=1000)
    items: list[PosOrderItemCreate] = Field(min_length=1)
    payment: PosPaymentCreate


class PosOrderModifierResponse(BaseModel):
    group_name: str
    option_name: str
    price_delta: Decimal


class PosOrderItemResponse(BaseModel):
    product_id: int | None
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    modifiers: list[PosOrderModifierResponse]


class PosPaymentResponse(BaseModel):
    method: str
    amount: Decimal
    amount_tendered: Decimal | None
    change_due: Decimal | None
    external_reference: str | None


class PosOrderResponse(BaseModel):
    id: int
    order_uuid: str
    folio: str
    branch_code: str
    terminal_id: str
    customer_uuid: str | None = None
    status: str
    payment_status: str
    subtotal: Decimal
    total: Decimal
    currency: str
    created_at_client: datetime
    items: list[PosOrderItemResponse]
    payment: PosPaymentResponse
