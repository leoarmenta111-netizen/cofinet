from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.payment import GuestCheckoutResponse
from app.schemas.purchase import GuestPurchaseStatusResponse, PurchaseCreate
from app.services.plan_service import PlanService
from app.services.payment_service import PaymentService
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/guest-purchases", tags=["Guest Purchases"])


@router.post(
    "",
    response_model=GuestCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a guest purchase and Mercado Pago Checkout preference",
    responses={
        404: {"description": "Plan not found"},
        500: {"description": "Database error"},
        502: {"description": "Mercado Pago preference error"},
    },
)
def create_guest_purchase(
    purchase: PurchaseCreate,
    db: Session = Depends(get_db),
) -> GuestCheckoutResponse:
    """Create a pending guest purchase and its Mercado Pago Checkout preference."""
    created_purchase = PurchaseService.create_guest_purchase(db, purchase)
    created_purchase.plan = PlanService.get_active_plan(db, created_purchase.plan_id)
    checkout = PaymentService.create_mercadopago_checkout(db, created_purchase)
    return GuestCheckoutResponse(
        purchase_id=created_purchase.id,
        checkout_url=checkout.checkout_url,
        payment_status=checkout.payment_status,
    )


@router.get(
    "/{purchase_id}",
    response_model=GuestPurchaseStatusResponse,
    response_model_exclude_none=True,
    summary="Poll a guest purchase payment status",
    responses={404: {"description": "Purchase not found"}},
)
def get_guest_purchase_status(
    purchase_id: int,
    db: Session = Depends(get_db),
) -> GuestPurchaseStatusResponse:
    return PurchaseService.get_guest_purchase_status(db, purchase_id)
