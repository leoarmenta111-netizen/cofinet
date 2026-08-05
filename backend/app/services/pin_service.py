from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import Purchase, PurchaseStatus
from app.schemas.pin import PinValidationResponse
from app.services.purchase_service import PurchaseService


class PinService:
    @staticmethod
    def validate(db: Session, pin_code: str) -> PinValidationResponse:
        """Validate a PIN and return the access details it grants."""
        purchase = db.execute(
            select(Purchase)
            .options(joinedload(Purchase.plan))
            .where(Purchase.pin_code == pin_code)
        ).scalar_one_or_none()

        if purchase is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PIN not found",
            )

        now = datetime.now(UTC)
        if purchase.expires_at is not None and purchase.expires_at.tzinfo is None:
            now = datetime.now()
        if purchase.status == PurchaseStatus.EXPIRED or (
            purchase.expires_at is not None and purchase.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="PIN expired",
            )

        # A paid purchase with a future expiry is the application's existing
        # definition of an active purchase (also used by the admin dashboard).
        if purchase.status != PurchaseStatus.PAID or purchase.expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="PIN inactive",
            )

        return PinValidationResponse(
            purchase_id=purchase.id,
            plan=purchase.plan.name,
            minutes=PurchaseService.issued_duration_minutes(purchase),
            expires_at=purchase.expires_at,
        )
