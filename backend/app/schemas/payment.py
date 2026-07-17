from pydantic import BaseModel


class GuestCheckoutResponse(BaseModel):
    purchase_id: int
    checkout_url: str
    payment_status: str
