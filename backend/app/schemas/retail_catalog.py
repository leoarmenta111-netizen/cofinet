from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RetailPriceQuote(BaseModel):
    unit_price: Decimal
    line_total: Decimal
    pricing_rule: Literal[
        "SALE_PRICE",
        "BULK_PRICE",
        "SERVICE_TIER",
    ]


class RetailPresentationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    item_id: int
    branch_id: int
    name: str
    barcode: str | None
    conversion_factor: Decimal
    sale_price: Decimal
    bulk_price: Decimal | None
    bulk_min_quantity: Decimal | None
    is_default: bool
    is_active: bool


class RetailServicePriceTierResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    item_id: int
    min_quantity: Decimal
    max_quantity: Decimal | None
    unit_price: Decimal


class RetailCatalogItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    branch_id: int
    item_type: Literal[
        "PRODUCT",
        "SERVICE",
    ]
    sku: str | None
    name: str
    description: str | None
    category: str | None
    base_unit_code: str
    cost: Decimal
    inventory_tracked: bool
    low_stock_threshold: Decimal | None
    max_stock: Decimal | None
    is_active: bool
    presentations: list[
        RetailPresentationResponse
    ] = []
    service_price_tiers: list[
        RetailServicePriceTierResponse
    ] = []
