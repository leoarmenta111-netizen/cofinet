from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


RetailSaleStatus = Literal[
    "HELD",
    "PAID",
    "PARTIALLY_RETURNED",
    "RETURNED",
    "CANCELLED",
]

RetailPaymentMethod = Literal[
    "CASH",
    "CARD",
]

RetailSaleItemType = Literal[
    "PRODUCT",
    "SERVICE",
]


class RetailSaleLineResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    item_id: int | None
    item_type: RetailSaleItemType
    sku: str | None
    item_name: str
    presentation_id: int | None
    presentation_name: str | None
    barcode: str | None
    conversion_factor: Decimal
    quantity: Decimal
    unit_price: Decimal
    line_subtotal: Decimal
    discount_amount: Decimal
    line_total: Decimal
    unit_cost_snapshot: Decimal


class RetailPaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    payment_uuid: str
    method: RetailPaymentMethod
    amount: Decimal
    amount_tendered: Decimal | None
    change_due: Decimal
    external_reference: str | None


class RetailReturnLineResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    sale_line_id: int
    quantity: Decimal
    unit_amount: Decimal
    line_total: Decimal


class RetailReturnResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    return_uuid: str
    sale_id: int
    cashier_staff_id: int
    authorizer_staff_id: int
    reason: str
    subtotal: Decimal
    total: Decimal
    created_at: datetime
    lines: list[
        RetailReturnLineResponse
    ] = []


class RetailSaleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    sale_uuid: str
    branch_id: int
    module_code: Literal["PAPELERIA"]
    terminal_id: str
    cashier_staff_id: int
    status: RetailSaleStatus
    label: str | None
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    currency: Literal["MXN"]
    receipt_snapshot: dict[
        str,
        Any,
    ] | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[
        RetailSaleLineResponse
    ] = []
    payments: list[
        RetailPaymentResponse
    ] = []
    returns: list[
        RetailReturnResponse
    ] = []


class RetailHeldSaleLineInput(BaseModel):
    item_id: int
    presentation_id: int | None = None
    quantity: Decimal


class RetailHeldSaleUpsert(BaseModel):
    label: str | None = None
    lines: list[RetailHeldSaleLineInput]


class RetailCheckoutLineInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    item_id: int
    presentation_id: int | None = None
    quantity: Decimal
    discount_amount: Decimal = Decimal(
        "0.00"
    )


class RetailCheckoutRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    sale_uuid: str
    held_sale_uuid: str | None = None
    lines: list[RetailCheckoutLineInput]
    sale_discount_amount: Decimal = Decimal(
        "0.00"
    )
    payment_uuid: str
    payment_method: RetailPaymentMethod
    amount_tendered: Decimal | None = None
    external_reference: str | None = None
    authorizing_manager_staff_id: int | None = None
    manager_pin: str | None = None
    authorizing_manager_staff_id: int | None = None
    manager_pin: str | None = None
