from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.admin_access import PinBatchStatus


class PinBatchCreate(BaseModel):
    plan_id: int = Field(gt=0)
    branch_code: str | None = Field(default=None, max_length=50)
    quantity: int = Field(default=100, ge=1, le=100)
    request_id: UUID


class PinBatchTicket(BaseModel):
    purchase_id: int
    pin: str
    plan_name: str
    duration_minutes: int
    amount: Decimal
    issued_at: datetime | None = None
    expires_at: datetime | None = None


class PinBatchPrintableTicket(BaseModel):
    pin: str
    plan_name: str
    duration_minutes: int
    amount: Decimal
    issued_at: datetime | None = None
    expires_at: datetime | None = None


class PinBatchFailureResponse(BaseModel):
    pin: str | None
    error_code: str
    message: str


class PinBatchSummaryResponse(BaseModel):
    id: int
    batch_uuid: UUID
    request_id: UUID
    branch_id: int
    branch_code: str
    branch_name: str
    plan_id: int
    plan_name: str
    requested: int
    created: int
    failed: int
    status: PinBatchStatus
    created_by_admin_id: int | None
    created_by_admin_name: str | None
    created_at: datetime
    completed_at: datetime | None


class PinBatchDetailResponse(PinBatchSummaryResponse):
    pins: list[PinBatchTicket]
    failures: list[PinBatchFailureResponse]


class PinBatchListResponse(BaseModel):
    batches: list[PinBatchSummaryResponse]


class PinBatchPrintResponse(BaseModel):
    batch_uuid: UUID
    branch_id: int
    branch_code: str
    branch_name: str
    plan_name: str
    generated_at: datetime
    tickets: list[PinBatchPrintableTicket]


class InternalAccessCreate(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    branch_code: str | None = Field(default=None, max_length=50)
    request_id: UUID

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Device label is required")
        return normalized


class InternalAccessStatusUpdate(BaseModel):
    is_active: bool


class InternalAccessResponse(BaseModel):
    id: int
    branch_id: int
    branch_code: str
    branch_name: str
    label: str
    pin: str
    is_active: bool
    created_by_admin_id: int | None
    created_by_admin_name: str | None
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    creation_source: Literal["internal_device"] = "internal_device"
    permanent: Literal[True] = True
    non_revenue: Literal[True] = True
    expires_at: None = None


class InternalAccessListResponse(BaseModel):
    credentials: list[InternalAccessResponse]
