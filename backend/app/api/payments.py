from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receive Mercado Pago payment notifications",
    responses={
        200: {"description": "Notification processed or safely ignored"},
        502: {"description": "Mercado Pago payment verification failed"},
    },
)
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Verifies the payment with Mercado Pago before changing local records."""
    try:
        payload: Any = await request.json()
    except ValueError:
        payload = {}
    PaymentService.process_mercadopago_webhook(
        db,
        payload if isinstance(payload, dict) else {},
    )
    return {"status": "ok"}
