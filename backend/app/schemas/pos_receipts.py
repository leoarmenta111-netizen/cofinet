from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_serializer, field_validator


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
