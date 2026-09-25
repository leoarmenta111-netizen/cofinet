from datetime import datetime
from decimal import Decimal
from typing import Literal
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


class SelfOrderCancelRequest(BaseModel):
    device_code: str = Field(
        min_length=1,
        max_length=80,
    )


class SelfOrderPaymentAttemptCreate(BaseModel):
    device_code: str = Field(
        min_length=1,
        max_length=80,
    )
    payment_attempt_uuid: UUID
    simulated_outcome: Literal[
        'APPROVED',
        'DECLINED',
        'UNKNOWN',
    ]


class SelfOrderModifierResponse(BaseModel):
    group_name: str
    option_name: str
    price_delta: Decimal


class SelfOrderItemResponse(BaseModel):
    product_id: int | None
    product_name: str
    preparation_station: Literal[
        'KITCHEN',
        'BAR',
        'NONE',
    ]
    quantity: int
    unit_base_price: Decimal
    unit_modifier_total: Decimal
    unit_price: Decimal
    line_total: Decimal
    notes: str | None
    modifiers: list[
        SelfOrderModifierResponse
    ]


class SelfOrderResponse(BaseModel):
    self_order_uuid: str
    branch_code: str
    device_code: str
    source: Literal[
        'KIOSK',
        'BAR_TABLET',
    ]
    status: Literal[
        'AWAITING_PAYMENT',
        'PAYMENT_PROCESSING',
        'PAYMENT_DECLINED',
        'PAYMENT_UNKNOWN',
        'PAID',
        'SUBMITTED',
        'CANCELLED',
        'EXPIRED',
    ]
    subtotal: Decimal
    total: Decimal
    currency: str
    expires_at: datetime
    created_at: datetime
    items: list[SelfOrderItemResponse]
    folio: str | None
    pos_order_uuid: str | None
