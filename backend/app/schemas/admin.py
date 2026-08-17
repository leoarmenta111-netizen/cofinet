from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.admin import AdminRole
from app.models.purchase import PurchaseCreationSource


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: AdminRole


class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    created_by_admin_id: int | None


class AdminCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: AdminRole = AdminRole.PIN_OPERATOR
    confirm_super_admin: bool = False

    @model_validator(mode="after")
    def require_super_admin_confirmation(self) -> "AdminCreate":
        if self.role == AdminRole.SUPER_ADMIN and not self.confirm_super_admin:
            raise ValueError("Creating a super administrator requires explicit confirmation")
        return self


class AdminStatusUpdate(BaseModel):
    is_active: bool


class AdminRoleUpdate(BaseModel):
    role: AdminRole
    confirm_super_admin: bool = False

    @model_validator(mode="after")
    def require_super_admin_confirmation(self) -> "AdminRoleUpdate":
        if self.role == AdminRole.SUPER_ADMIN and not self.confirm_super_admin:
            raise ValueError("Assigning the super administrator role requires confirmation")
        return self


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


class AdminDashboardResponse(BaseModel):
    total_sales_today: Decimal
    total_sales_week: Decimal
    total_sales_month: Decimal
    active_purchases: int
    expired_purchases: int
    active_pins: int
    pending_mercadopago_payments: int


class AdminPinCreate(BaseModel):
    plan_id: int = Field(gt=0)
    branch_code: str | None = Field(default=None, max_length=50)


class AdminPinResponse(BaseModel):
    purchase_id: int
    branch_id: int
    branch_code: str
    branch_name: str
    plan_id: int
    plan_name: str
    duration_minutes: int
    pin: str
    issued_at: datetime
    expires_at: datetime
    amount: Decimal
    creation_source: PurchaseCreationSource
    created_by_admin_id: int | None
    created_by_admin_name: str | None


class AdminPinList(BaseModel):
    pins: list[AdminPinResponse]


class AdminPaymentResponse(BaseModel):
    payment_id: int
    purchase_id: int
    provider: str
    provider_payment_id: str | None
    provider_preference_id: str
    amount: Decimal
    currency: str
    status: str
    plan_name: str
    purchase_status: str
    created_at: datetime
    updated_at: datetime


class AdminPaymentList(BaseModel):
    payments: list[AdminPaymentResponse]
