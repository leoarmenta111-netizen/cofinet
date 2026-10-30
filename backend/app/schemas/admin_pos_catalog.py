from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AdminPosCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class AdminPosCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosProductCreate(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=80)
    base_price: Decimal = Field(ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    preparation_station: Literal[
        "KITCHEN",
        "BAR",
        "NONE",
    ] = "NONE"
    sort_order: int = 0
    is_active: bool = True


class AdminPosProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=80)
    base_price: Decimal | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    preparation_station: Literal[
        "KITCHEN",
        "BAR",
        "NONE",
    ] | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosBranchProductUpdate(BaseModel):
    price: Decimal | None = Field(default=None, ge=0)
    is_available: bool = True
    sort_order: int = 0


class AdminPosProductVariantUpdate(BaseModel):
    price: Decimal = Field(ge=0)
    is_active: bool = True
    sort_order: int = 0


class AdminPosBranchProductVariantUpdate(BaseModel):
    price_override: Decimal | None = Field(default=None, ge=0)
    is_available: bool = True


class AdminPosVariantGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    is_active: bool = True


class AdminPosVariantGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sort_order: int = 0
    is_active: bool = True


class AdminPosVariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosModifierGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    required: bool = False
    min_select: int = Field(default=0, ge=0)
    max_select: int = Field(default=1, ge=1)
    sort_order: int = 0
    is_active: bool = True


class AdminPosModifierGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    required: bool | None = None
    min_select: int | None = Field(default=None, ge=0)
    max_select: int | None = Field(default=None, ge=1)
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosModifierOptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price_delta: Decimal = Field(default=Decimal("0.00"))
    sort_order: int = 0
    is_active: bool = True


class AdminPosModifierOptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_delta: Decimal | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosProductModifierUpdate(BaseModel):
    enabled: bool = True
    sort_order: int = 0


class AdminPosBranchSettingResponse(BaseModel):
    branch_id: int
    branch_code: str
    branch_name: str
    price: Decimal | None
    effective_price: Decimal
    is_available: bool
    sort_order: int


class AdminPosCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    sort_order: int
    is_active: bool


class AdminPosVariantResponse(BaseModel):
    id: int
    variant_group_id: int
    name: str
    sort_order: int
    is_active: bool


class AdminPosVariantGroupResponse(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool
    variants: list[AdminPosVariantResponse]


class AdminPosModifierOptionResponse(BaseModel):
    id: int
    name: str
    price_delta: Decimal
    image_url: str | None
    sort_order: int
    is_active: bool


class AdminPosModifierGroupResponse(BaseModel):
    id: int
    name: str
    required: bool
    min_select: int
    max_select: int
    sort_order: int
    is_active: bool
    options: list[AdminPosModifierOptionResponse]


class AdminPosProductModifierResponse(BaseModel):
    group_id: int
    group_name: str
    sort_order: int


class AdminPosBranchProductVariantResponse(BaseModel):
    branch_code: str
    branch_name: str
    price_override: Decimal | None
    effective_price: Decimal
    is_available: bool


class AdminPosProductVariantResponse(BaseModel):
    product_variant_id: int
    variant_id: int
    variant_name: str
    price: Decimal
    is_active: bool
    sort_order: int
    branches: list[AdminPosBranchProductVariantResponse]


class AdminPosProductResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    name: str
    description: str | None
    sku: str | None
    base_price: Decimal
    image_url: str | None
    preparation_station: Literal[
        "KITCHEN",
        "BAR",
        "NONE",
    ]
    sort_order: int
    is_active: bool
    variant_group_id: int | None
    variants: list[AdminPosProductVariantResponse]
    branches: list[AdminPosBranchSettingResponse]
    modifiers: list[AdminPosProductModifierResponse]


class AdminPosCatalogBranchResponse(BaseModel):
    id: int
    code: str
    name: str


class AdminPosCatalogResponse(BaseModel):
    branches: list[AdminPosCatalogBranchResponse]
    categories: list[AdminPosCategoryResponse]
    products: list[AdminPosProductResponse]
    modifier_groups: list[AdminPosModifierGroupResponse]
    variant_groups: list[AdminPosVariantGroupResponse]
