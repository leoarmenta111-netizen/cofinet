from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_serializer, field_validator, Field, model_validator


TaxMode = Literal["NONE", "INCLUDED", "ADDED"]


class ReceiptSettingsUpdate(BaseModel):
    business_name: str
    logo_ref: str | None = None
    phone: str | None = None
    web_social: str | None = None
    footer_message: str | None = None
    currency: str
    tax_mode: TaxMode
    tax_rate: float
    receipt_width_mm: Literal[80]
    timezone: str
    folio_prefix: str
    auto_print_customer: bool

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate(cls, value: float) -> float:
        if value < 0:
            raise ValueError("tax_rate must be nonnegative")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Invalid timezone") from exc
        return value

    @field_validator("folio_prefix")
    @classmethod
    def validate_folio_prefix(cls, value: str) -> str:
        value = value.upper()

        if not 2 <= len(value) <= 8:
            raise ValueError("folio_prefix must be 2 to 8 characters")

        if not value.isascii() or not value.isalnum():
            raise ValueError("folio_prefix must be ASCII alphanumeric")

        return value


class EffectiveReceiptSettings(BaseModel):
    business_name: str
    logo_ref: str | None = None
    phone: str | None = None
    web_social: str | None = None
    footer_message: str | None = None
    branch_code: str
    branch_name: str
    address: str | None = None
    currency: str
    tax_mode: TaxMode
    tax_rate: Decimal
    receipt_width_mm: int
    timezone: str
    folio_prefix: str
    auto_print_customer: bool

    @field_serializer("tax_rate", when_used="json")
    def serialize_tax_rate(self, value: Decimal) -> float:
        return float(value)


class BranchReceiptSettingsUpdate(BaseModel):
    display_name: str | None = None
    address: str | None = None
    phone: str | None = None
    web_social: str | None = None
    footer_message: str | None = None
    tax_mode: TaxMode | None = None
    tax_rate: float | None = None
    timezone: str | None = None
    folio_prefix: str | None = None
    auto_print_customer: bool | None = None

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("tax_rate must be nonnegative")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Invalid timezone") from exc
        return value

    @field_validator("folio_prefix")
    @classmethod
    def validate_folio_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.upper()

        if not 2 <= len(value) <= 8:
            raise ValueError("folio_prefix must be 2 to 8 characters")

        if not value.isascii() or not value.isalnum():
            raise ValueError("folio_prefix must be ASCII alphanumeric")

        return value


class ReceiptSnapshotBusinessV1(BaseModel):
    business_name: str
    logo_ref: str | None = None
    phone: str | None = None
    web_social: str | None = None
    footer_message: str | None = None


class ReceiptSnapshotBranchV1(BaseModel):
    branch_code: str
    branch_name: str
    address: str | None = None
    phone: str | None = None


class ReceiptSnapshotFiscalV1(BaseModel):
    rfc: str
    fiscal_address: str
    billing_label: str
    billing_message: str
    billing_url: str
    billing_qr_ref: str

    model_config = {"extra": "forbid"}


class ReceiptSnapshotTerminalV1(BaseModel):
    terminal_id: str


class ReceiptSnapshotCustomerV1(BaseModel):
    name: str

    model_config = {"extra": "forbid"}


class ReceiptSnapshotModifierV1(BaseModel):
    modifier_group_id: int | None = None
    modifier_option_id: int | None = None
    group_name: str | None = None
    option_name: str
    price_delta_cents: int = Field(ge=0)

    model_config = {"extra": "forbid"}


class ReceiptSnapshotItemV1(BaseModel):
    product_id: int
    product_variant_id: int | None = None
    variant_name: str | None = None
    product_name: str
    quantity: int = Field(ge=1)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)
    modifiers: list[ReceiptSnapshotModifierV1] = []

    @model_validator(mode="after")
    def validate_variant_identity(self):
        has_variant_id = (
            self.product_variant_id is not None
        )
        has_variant_name = (
            self.variant_name is not None
        )

        if has_variant_id != has_variant_name:
            raise ValueError(
                "product variant identity requires "
                "both product_variant_id and variant_name"
            )

        if (
            self.variant_name is not None
            and not self.variant_name.strip()
        ):
            raise ValueError(
                "variant_name cannot be blank"
            )

        return self

    model_config = {"extra": "forbid"}


class ReceiptSnapshotTotalsV1(BaseModel):
    subtotal_cents: int = Field(ge=0)
    discount_cents: int = Field(default=0, ge=0)
    tax_mode: Literal["NONE", "INCLUDED", "ADDED"]
    tax_rate: Decimal = Field(ge=0)
    tax_cents: int = Field(ge=0)
    tip_cents: int = Field(ge=0)
    total_cents: int = Field(ge=0)

    model_config = {"extra": "forbid"}


class ReceiptSnapshotPaymentV1(BaseModel):
    method: Literal["CASH", "CARD_EXTERNAL"]
    amount_cents: int = Field(ge=0)
    amount_tendered_cents: int | None = Field(default=None, ge=0)
    change_due_cents: int | None = Field(default=None, ge=0)

    model_config = {"extra": "forbid"}


class ReceiptSnapshotV1(BaseModel):
    schema_version: Literal[1]
    order_type: Literal["DINE_IN", "TAKEOUT", "DELIVERY"] | None = None
    order_name: str | None = Field(default=None, max_length=120)
    table_number: str | None = Field(default=None, max_length=80)
    order_uuid: UUID
    folio: str = Field(min_length=8, max_length=40)
    sold_at: datetime
    currency: str = Field(min_length=3, max_length=3)
    business: ReceiptSnapshotBusinessV1
    branch: ReceiptSnapshotBranchV1
    terminal: ReceiptSnapshotTerminalV1
    fiscal: ReceiptSnapshotFiscalV1 | None = None
    customer: ReceiptSnapshotCustomerV1 | None = None
    items: list[ReceiptSnapshotItemV1] = Field(min_length=1)
    totals: ReceiptSnapshotTotalsV1
    payment: ReceiptSnapshotPaymentV1

    model_config = {"extra": "forbid"}
