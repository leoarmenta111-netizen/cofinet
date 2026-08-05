from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
import logging
import secrets

from app.services.mikrotik_service import MikroTikService, MikroTikUserExistsError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from app.models.user import User
from app.schemas.purchase import (
    GuestPurchaseResponse,
    GuestPurchaseStatusResponse,
    PurchaseCreate,
    PurchaseResponse,
)
from app.services.plan_service import PlanService


logger = logging.getLogger(__name__)


class PurchaseService:
    _PIN_GENERATION_ATTEMPTS = 10

    @staticmethod
    def create_purchase(
        db: Session,
        user: User,
        purchase_data: PurchaseCreate,
    ) -> Purchase:
        plan = PlanService.get_active_plan(db, purchase_data.plan_id)
        expires_at = datetime.now(UTC) + timedelta(minutes=plan.duration_minutes)

        for _ in range(PurchaseService._PIN_GENERATION_ATTEMPTS):
            pin_code = PurchaseService._generate_pin()
            if PurchaseService._pin_exists(db, pin_code):
                continue

            purchase = Purchase(
                user_id=user.id,
                plan_id=plan.id,
                amount=plan.price,
                status=PurchaseStatus.PAID,
                pin_code=pin_code,
                expires_at=expires_at,
                creation_source=PurchaseCreationSource.SYSTEM,
            )
            try:
                db.add(purchase)
                db.commit()
                db.refresh(purchase)
                return purchase
            except IntegrityError:
                # The unique database constraint also protects against concurrent requests.
                db.rollback()
            except SQLAlchemyError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not create purchase",
                ) from exc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique PIN",
        )

    @staticmethod
    def create_guest_purchase(db: Session, purchase_data: PurchaseCreate) -> Purchase:
        """Create a pending guest purchase without granting access credentials."""
        plan = PlanService.get_active_plan(db, purchase_data.plan_id)
        purchase = Purchase(
            plan_id=plan.id,
            amount=plan.price,
            status=PurchaseStatus.PENDING,
            creation_source=PurchaseCreationSource.MERCADOPAGO,
        )
        try:
            db.add(purchase)
            db.commit()
            db.refresh(purchase)
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create guest purchase",
            ) from exc
        return purchase

    
    @staticmethod
    def mark_guest_purchase_paid(db: Session, purchase: Purchase) -> None:
        """Issue one unique credential and create its MikroTik Hotspot user."""
        issued_at = datetime.now(UTC)

        for _ in range(PurchaseService._PIN_GENERATION_ATTEMPTS):
            pin_code = PurchaseService._generate_pin()

            if PurchaseService._pin_exists(db, pin_code):
                continue

            mikrotik = None
            mikrotik_user_created = False

            try:
                mikrotik = MikroTikService()

                mikrotik.create_hotspot_user_strict(
                    username=pin_code,
                    password=pin_code,
                    duration_minutes=purchase.plan.duration_minutes,
                    profile="default",
                    comment="CofiCenter Mercado Pago purchase",
                )
                mikrotik_user_created = True

                purchase.status = PurchaseStatus.PAID
                purchase.pin_code = pin_code
                purchase.issued_at = issued_at
                purchase.expires_at = issued_at + timedelta(
                    minutes=purchase.plan.duration_minutes
                )
                db.flush()
                db.commit()

                return

            except (IntegrityError, MikroTikUserExistsError):
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate duplicate guest PIN %s", pin_code)
                continue

            except SQLAlchemyError as exc:
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate guest PIN %s", pin_code)
                logger.exception("Database rejected paid guest PIN %s", pin_code)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not confirm paid purchase",
                ) from exc

            except Exception as exc:
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate guest PIN %s", pin_code)
                logger.exception("MikroTik rejected paid guest PIN %s", pin_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Could not create PIN in MikroTik",
                ) from exc

            finally:
                if mikrotik is not None:
                    mikrotik.disconnect()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique PIN",
        )

    @staticmethod
    def get_purchase(db: Session, user_id: int, purchase_id: int) -> Purchase:
        purchase = db.execute(
            select(Purchase)
            .options(joinedload(Purchase.plan))
            .where(Purchase.id == purchase_id, Purchase.user_id == user_id)
        ).scalar_one_or_none()
        if purchase is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found",
            )
        return purchase

    @staticmethod
    def get_guest_purchase_status(db: Session, purchase_id: int) -> GuestPurchaseStatusResponse:
        purchase = db.execute(
            select(Purchase).where(Purchase.id == purchase_id)
        ).scalar_one_or_none()
        if purchase is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
        if purchase.status == PurchaseStatus.PAID:
            return GuestPurchaseStatusResponse(
                status=PurchaseStatus.PAID,
                pin=purchase.pin_code,
                expires_at=purchase.expires_at,
            )
        return GuestPurchaseStatusResponse(status=PurchaseStatus.PENDING)

    @staticmethod
    def list_purchases(db: Session, user_id: int) -> Sequence[Purchase]:
        return db.execute(
            select(Purchase)
            .options(joinedload(Purchase.plan))
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc(), Purchase.id.desc())
        ).scalars().all()

    @staticmethod
    def to_response(purchase: Purchase) -> PurchaseResponse:
        return PurchaseResponse(
            purchase_id=purchase.id,
            plan=purchase.plan.name,
            pin=purchase.pin_code,
            duration_minutes=PurchaseService.issued_duration_minutes(purchase),
            expires_at=purchase.expires_at,
            status=purchase.status,
        )

    @staticmethod
    def to_guest_response(purchase: Purchase) -> GuestPurchaseResponse:
        return GuestPurchaseResponse(
            purchase_id=purchase.id,
            plan=purchase.plan.name,
            amount=purchase.amount,
            status=purchase.status,
        )

    @staticmethod
    def _generate_pin() -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"

    @staticmethod
    def _pin_exists(db: Session, pin_code: str) -> bool:
        return db.execute(
            select(Purchase.id).where(Purchase.pin_code == pin_code)
        ).scalar_one_or_none() is not None

    @staticmethod
    def issued_duration_minutes(purchase: Purchase) -> int:
        """Return the immutable issued duration without changing legacy rows."""
        if purchase.issued_at is not None and purchase.expires_at is not None:
            return int((purchase.expires_at - purchase.issued_at).total_seconds() // 60)
        return purchase.plan.duration_minutes
