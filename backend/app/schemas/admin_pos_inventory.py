from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


InventoryStatus = Literal[
    "UNTRACKED",
    "AVAILABLE",
    "LOW_STOCK",
    "OUT_OF_STOCK",
    "REVIEW",
]


class AdminInventoryTrackingUpdate(BaseModel):
    is_tracked: bool
    low_stock_threshold: Decimal = Field(ge=0)
    initial_quantity: Decimal | None = Field(
        default=None,
        ge=0,
    )


class AdminInventoryReceiptCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class AdminInventoryWasteCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0)
    note: str = Field(min_length=1, max_length=500)


class AdminInventoryAdjustmentCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    physical_quantity: Decimal
    note: str = Field(min_length=1, max_length=500)


class AdminInventoryRowResponse(BaseModel):
    item_id: int
    product_id: int | None
    product_name: str
    branch_id: int
    branch_code: str
    branch_name: str
    is_tracked: bool
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal
    status: InventoryStatus
    updated_at: datetime


class AdminInventoryMovementResponse(BaseModel):
    id: int
    movement_type: str
    quantity_delta: Decimal
    balance_after: Decimal
    order_id: int | None
    order_item_id: int | None
    order_uuid: str | None
    folio: str | None
    note: str | None
    created_by_admin_id: int | None
    created_at: datetime
