from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.pos_staff import PosStaffRole


class PosStaffUnlockRequest(BaseModel):
    staff_id: int = Field(gt=0)
    pin: str = Field(min_length=4, max_length=32)
    branch_code: str = Field(min_length=1, max_length=50)
    terminal_id: str = Field(min_length=1, max_length=80)

    @field_validator("branch_code", "terminal_id")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value is required")

        return normalized


class PosStaffUnlockResponse(BaseModel):
    staff_id: int
    display_name: str
    role: PosStaffRole
    branch_code: str
    terminal_id: str
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class PosStaffSessionResponse(BaseModel):
    staff_id: int
    display_name: str
    role: PosStaffRole
    branch_code: str
    terminal_id: str
