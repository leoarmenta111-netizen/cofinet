from datetime import date

from pydantic import BaseModel, ConfigDict


class AdminPosCustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    birthday: date | None = None


class AdminPosCustomerResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    customer_uuid: str
    name: str
    phone: str
    phone_normalized: str
    email: str | None = None
    birthday: date | None = None
