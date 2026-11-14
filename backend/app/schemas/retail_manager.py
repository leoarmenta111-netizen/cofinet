from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


RetailManagerInventoryStatus = Literal[
    "AVAILABLE",
    "LOW_STOCK",
    "OUT_OF_STOCK",
    "REVIEW",
]


class RetailManagerStaffResponse(BaseModel):
    id: int
    display_name: str
    role: Literal["MANAGER"]


class RetailManagerInventoryRowResponse(BaseModel):
    item_id: int
    sku: str | None
    item_name: str
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal | None
    max_stock: Decimal | None
    status: RetailManagerInventoryStatus


class RetailManagerInventoryMovementResponse(BaseModel):
    id: int
    item_id: int
    movement_type: str
    quantity_delta: Decimal
    balance_after: Decimal
    note: str | None
    actor_staff_id: int | None
    authorizer_staff_id: int | None
    created_by_admin_id: int | None
    idempotency_key: str | None
    created_at: datetime


class RetailManagerAuthorization(BaseModel):
    authorizing_manager_staff_id: int = Field(
        gt=0,
    )
    manager_pin: str = Field(
        min_length=1,
        max_length=64,
    )
    idempotency_key: str = Field(
        min_length=1,
        max_length=120,
    )
    note: str = Field(
        min_length=1,
        max_length=500,
    )


class RetailManagerInventoryEntryRequest(
    RetailManagerAuthorization
):
    quantity: Decimal = Field(
        gt=0,
        decimal_places=3,
    )


class RetailManagerInventoryRemovalRequest(
    RetailManagerAuthorization
):
    quantity: Decimal = Field(
        gt=0,
        decimal_places=3,
    )


class RetailManagerInventoryAdjustmentRequest(
    RetailManagerAuthorization
):
    physical_quantity: Decimal = Field(
        ge=0,
        decimal_places=3,
    )
