from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import (
    Purchase,
    PurchaseCreationSource,
    PurchaseStatus,
)
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

        # Legacy admin-batch PINs were created before activation
        # timestamps were stored. Start their validity window on
        # first portal validation and never reset it afterward.
        if (
            purchase.status == PurchaseStatus.PAID
            and purchase.creation_source
            == PurchaseCreationSource.ADMIN_BATCH
            and purchase.issued_at is None
            and purchase.expires_at is None
        ):
            activated_at = datetime.now(UTC)
            expires_at = activated_at + timedelta(
                minutes=purchase.plan.duration_minutes
            )

            try:
                db.execute(
                    update(Purchase)
                    .where(
                        Purchase.id == purchase.id,
                        Purchase.status
                        == PurchaseStatus.PAID,
                        Purchase.creation_source
                        == PurchaseCreationSource.ADMIN_BATCH,
                        Purchase.issued_at.is_(None),
                        Purchase.expires_at.is_(None),
                    )
                    .values(
                        issued_at=activated_at,
                        expires_at=expires_at,
                    )
                )
                db.commit()
                db.refresh(purchase)
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not activate PIN",
                ) from exc

        # A paid purchase with a future expiry is the application's existing
        # definition of an active purchase (also used by the admin dashboard).
        if (
            purchase.status != PurchaseStatus.PAID
            or purchase.expires_at is None
        ):
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
