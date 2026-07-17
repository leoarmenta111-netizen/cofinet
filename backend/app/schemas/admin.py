from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AdminLogin(BaseModel):
    email: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str


class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class AdminDashboardResponse(BaseModel):
    total_sales_today: Decimal
    active_purchases: int
    expired_purchases: int
    active_pins: int
    pending_mercadopago_payments: int


class AdminPinCreate(BaseModel):
    plan_id: int = Field(gt=0)


class AdminPinResponse(BaseModel):
    purchase_id: int
    plan_id: int
    plan_name: str
    pin: str
    issued_at: datetime
    expires_at: datetime
    amount: Decimal


class AdminPinList(BaseModel):
    pins: list[AdminPinResponse]
