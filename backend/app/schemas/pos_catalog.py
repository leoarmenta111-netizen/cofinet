from decimal import Decimal

from pydantic import BaseModel


class PosCatalogBranchResponse(BaseModel):
    id: int
    code: str
    name: str


class PosModifierOptionResponse(BaseModel):
    id: int
    name: str
    price_delta: Decimal
    sort_order: int


class PosModifierGroupResponse(BaseModel):
    id: int
    name: str
    required: bool
    min_select: int
    max_select: int
    sort_order: int
    options: list[PosModifierOptionResponse]


class PosCatalogProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sku: str | None
    price: Decimal
    image_url: str | None
    sort_order: int
    modifiers: list[PosModifierGroupResponse]


class PosCatalogCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    sort_order: int
    products: list[PosCatalogProductResponse]


class PosCatalogResponse(BaseModel):
    branch: PosCatalogBranchResponse
    categories: list[PosCatalogCategoryResponse]
