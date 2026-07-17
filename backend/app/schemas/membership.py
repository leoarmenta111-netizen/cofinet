from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, model_validator


class MembershipCheckoutRequest(BaseModel):
    plan: str
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "MembershipCheckoutRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class MembershipCheckoutResponse(BaseModel):
    membership_id: int
    checkout_url: str


class MembershipPlan(BaseModel):
    code: str
    name: str
    monthly_amount: Decimal
