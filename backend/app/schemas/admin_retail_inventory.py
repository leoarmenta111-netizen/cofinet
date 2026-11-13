from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


AdminRetailInventoryStatus = Literal[
    "AVAILABLE",
    "LOW_STOCK",
    "OUT_OF_STOCK",
    "REVIEW",
]


class AdminRetailInventoryEntryCreate(BaseModel):
    branch_code: str = Field(
        min_length=1,
        max_length=50,
    )
    quantity: Decimal = Field(
        gt=0,
        decimal_places=3,
    )
    note: str | None = Field(
        default=None,
        max_length=500,
    )
    idempotency_key: str = Field(
        min_length=1,
        max_length=100,
    )


class AdminRetailInventoryRemovalCreate(BaseModel):
    branch_code: str = Field(
        min_length=1,
        max_length=50,
    )
    quantity: Decimal = Field(
        gt=0,
        decimal_places=3,
    )
    note: str = Field(
        min_length=1,
        max_length=500,
    )
    idempotency_key: str = Field(
        min_length=1,
        max_length=100,
    )


class AdminRetailInventoryAdjustmentCreate(BaseModel):
    branch_code: str = Field(
        min_length=1,
        max_length=50,
    )
    physical_quantity: Decimal = Field(
        ge=0,
        decimal_places=3,
    )
    note: str = Field(
        min_length=1,
        max_length=500,
    )
    idempotency_key: str = Field(
        min_length=1,
        max_length=100,
    )


class AdminRetailInventoryRowResponse(BaseModel):
    item_id: int
    sku: str | None
    item_name: str
    branch_id: int
    branch_code: str
    branch_name: str
    inventory_tracked: bool
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal | None
    max_stock: Decimal | None
    status: AdminRetailInventoryStatus
    updated_at: datetime


class AdminRetailInventoryMovementResponse(BaseModel):
    id: int
    branch_id: int
    item_id: int
    movement_type: str
    quantity_delta: Decimal
    balance_after: Decimal
    sale_id: int | None
    sale_line_id: int | None
    note: str | None
    actor_staff_id: int | None
    authorizer_staff_id: int | None
    created_by_admin_id: int | None
    idempotency_key: str | None
    created_at: datetime
