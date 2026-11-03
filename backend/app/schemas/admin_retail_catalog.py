from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AdminRetailCatalogItemCreate(BaseModel):
    branch_id: int = Field(gt=0)
    item_type: Literal[
        "PRODUCT",
        "SERVICE",
    ]
    sku: str | None = Field(
        default=None,
        max_length=80,
    )
    name: str = Field(
        min_length=1,
        max_length=180,
    )
    description: str | None = None
    category: str | None = Field(
        default=None,
        max_length=120,
    )
    base_unit_code: str = Field(
        min_length=1,
        max_length=32,
    )
    cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=2,
    )
    inventory_tracked: bool = False
    low_stock_threshold: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=3,
    )
    max_stock: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=3,
    )
    is_active: bool = True


class AdminRetailPresentationCreate(BaseModel):
    branch_id: int = Field(gt=0)
    name: str = Field(
        min_length=1,
        max_length=120,
    )
    barcode: str | None = Field(
        default=None,
        max_length=120,
    )
    conversion_factor: Decimal = Field(
        gt=0,
        decimal_places=3,
    )
    sale_price: Decimal = Field(
        ge=0,
        decimal_places=2,
    )
    bulk_price: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    bulk_min_quantity: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=3,
    )
    is_default: bool = False
    is_active: bool = True


class AdminRetailServicePriceTierCreate(BaseModel):
    min_quantity: Decimal = Field(
        gt=0,
        decimal_places=3,
    )
    max_quantity: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=3,
    )
    unit_price: Decimal = Field(
        ge=0,
        decimal_places=2,
    )
