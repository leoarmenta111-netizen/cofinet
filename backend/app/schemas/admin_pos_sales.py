from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AdminPosSalesSummary(BaseModel):
    sales_count: int
    gross_total: Decimal
    cash_total: Decimal
    card_total: Decimal


class AdminPosSaleListItem(BaseModel):
    id: int
    order_uuid: str
    folio: str
    branch_code: str
    branch_name: str
    terminal_id: str
    status: str
    payment_status: str
    payment_method: str | None
    total: Decimal
    created_at: datetime
    created_at_client: datetime


class AdminPosSalesListResponse(BaseModel):
    summary: AdminPosSalesSummary
    sales: list[AdminPosSaleListItem]
    offset: int
    limit: int


class AdminPosSaleModifier(BaseModel):
    group_name: str
    option_name: str
    price_delta: Decimal


class AdminPosSaleItem(BaseModel):
    product_id: int | None
    product_name: str
    quantity: int
    unit_base_price: Decimal
    unit_modifier_total: Decimal
    unit_price: Decimal
    line_total: Decimal
    notes: str | None
    modifiers: list[AdminPosSaleModifier]


class AdminPosSalePayment(BaseModel):
    method: str
    amount: Decimal
    amount_tendered: Decimal | None
    change_due: Decimal | None
    external_reference: str | None


class AdminPosSaleDetailResponse(BaseModel):
    id: int
    order_uuid: str
    folio: str
    branch_code: str
    branch_name: str
    terminal_id: str
    status: str
    payment_status: str
    subtotal: Decimal
    total: Decimal
    currency: str
    notes: str | None
    created_at: datetime
    created_at_client: datetime

    items: list[AdminPosSaleItem]
    payment: AdminPosSalePayment | None
