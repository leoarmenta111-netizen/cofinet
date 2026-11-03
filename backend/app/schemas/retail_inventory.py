from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


RetailInventoryMovementType = Literal[
    "INITIAL",
    "MANUAL_ENTRY",
    "MANUAL_REMOVAL",
    "ADJUSTMENT",
    "SALE",
    "RETURN",
    "CANCELLATION_REVERSAL",
]


class RetailInventoryBalanceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    branch_id: int
    item_id: int
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal | None
    max_stock: Decimal | None


class RetailInventoryMovementResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    branch_id: int
    item_id: int
    movement_type: RetailInventoryMovementType
    quantity_delta: Decimal
    balance_after: Decimal
    sale_id: int | None
    sale_line_id: int | None
    note: str | None
    actor_staff_id: int | None
    authorizer_staff_id: int | None
    created_by_admin_id: int | None
    idempotency_key: str | None
