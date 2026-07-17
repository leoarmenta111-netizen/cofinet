from datetime import datetime

from pydantic import BaseModel, Field


class PinValidationRequest(BaseModel):
    pin: str = Field(min_length=1, max_length=6)


class PinValidationResponse(BaseModel):
    valid: bool = True
    purchase_id: int
    plan: str
    minutes: int
    expires_at: datetime


class PinValidationErrorResponse(BaseModel):
    valid: bool = False
    message: str
