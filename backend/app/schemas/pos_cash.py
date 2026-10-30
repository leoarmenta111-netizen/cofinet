from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    model_validator,
    BaseModel,
    ConfigDict,
    Field,
    model_serializer,
)


MxnDenominationCents = Literal[
    100,
    200,
    500,
    1000,
    2000,
    5000,
    10000,
    20000,
    50000,
    100000,
]


class CashDenominationCount(BaseModel):
    denomination_cents: MxnDenominationCents
    quantity: int = Field(ge=0, le=10000)


class PosCashShiftOpenRequest(BaseModel):
    opening_amount: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    opening_counts: list[CashDenominationCount] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
    )
    authorizing_manager_staff_id: int = Field(gt=0)
    manager_pin: str = Field(min_length=4, max_length=32)

    @model_validator(mode="after")
    def validate_opening_source(self):
        has_amount = self.opening_amount is not None
        has_counts = self.opening_counts is not None

        if has_amount == has_counts:
            raise ValueError(
                "Provide exactly one of opening_amount or opening_counts"
            )

        return self


class PosCashShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shift_uuid: str
    branch_id: int
    terminal_id: str
    status: Literal["OPEN", "CLOSING", "CLOSED"]
    opened_by_staff_id: int
    opening_authorized_by_staff_id: int
    opening_total: Decimal
    opened_at: datetime
    closed_at: datetime | None = None

    counted_cash: Decimal | None = Field(
        default=None,
        validation_alias="closing_total",
    )
    expected_cash: Decimal | None = Field(
        default=None,
        validation_alias="expected_total",
    )
    difference: Decimal | None = Field(
        default=None,
        validation_alias="variance",
    )

    @model_serializer(mode="wrap")
    def serialize_shift(self, handler):
        payload = handler(self)

        if self.status != "CLOSING":
            payload.pop("counted_cash", None)
            payload.pop("expected_cash", None)
            payload.pop("difference", None)

        return payload


class PosCashMovementRequest(BaseModel):
    direction: Literal["INFLOW", "OUTFLOW"]
    category: Literal[
        "CHANGE",
        "EXPENSE",
        "SAFE_WITHDRAWAL",
        "DEPOSIT",
        "CORRECTION",
        "OTHER",
    ]
    amount: Decimal = Field(gt=0)
    note: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(
        min_length=1,
        max_length=120,
    )
    authorizing_manager_staff_id: int = Field(gt=0)
    manager_pin: str = Field(min_length=4, max_length=32)


class PosCashMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_uuid: str
    shift_id: int
    direction: Literal["INFLOW", "OUTFLOW"]
    category: Literal[
        "CHANGE",
        "EXPENSE",
        "SAFE_WITHDRAWAL",
        "DEPOSIT",
        "CORRECTION",
        "OTHER",
    ]
    amount: Decimal
    note: str
    requesting_staff_id: int
    authorizing_staff_id: int
    idempotency_key: str
    created_at: datetime



class PosCashClosingCountRequest(BaseModel):
    closing_counts: list[CashDenominationCount] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
    )
    closing_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )


class PosCashReconciliation(BaseModel):
    shift_uuid: str
    status: Literal["CLOSING"]
    counted_cash: Decimal
    expected_cash: Decimal
    difference: Decimal


class PosCashCloseRequest(BaseModel):
    authorizing_manager_staff_id: int = Field(gt=0)
    manager_pin: str = Field(min_length=4, max_length=32)
    difference_note: str | None = Field(
        default=None,
        max_length=500,
    )
